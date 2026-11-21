import numpy as np
import pyvista as pv

import sys

from pyneuroml import pynml
from pyneuroml.utils import extract_position_info
from neuroml import Cell


def _rotation_matrix(rotate_x=0.0, rotate_y=0.0, rotate_z=0.0):
    """Combined rotation matrix for rotations (in degrees) about the x,
    y, then z axes, applied in that order (R = Rz @ Ry @ Rx)."""
    rx, ry, rz = np.radians([rotate_x, rotate_y, rotate_z])

    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)

    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])

    return Rz @ Ry @ Rx


def _transform(coords, rotation, factor):
    """Rotate coords (a (3,) or (N,3) array-like, NeuroML x/y/z) and
    scale by factor, for viewer display."""
    return np.asarray(coords, dtype=float) @ rotation.T * factor


_UNIT_SPHERE = pv.Sphere(radius=1.0)


def make_sphere(center, radius):
    """Build a sphere by scaling/translating a shared unit-sphere template.
    This avoids the overhead of creating a new pv.Sphere() for every soma
    in a network, which is the dominant cost of loading a model with many somas.
    Much more effich...
    """
    mesh = _UNIT_SPHERE.copy()
    mesh.points = (_UNIT_SPHERE.points * radius + np.asarray(center)).astype(np.float32)
    return mesh


def make_segment(
    pointa, pointb, radius_a, radius_b, n_sides=15, cap_a=True, cap_b=True
):
    """Return the raw (points, faces, normals) numpy arrays for a solid,
    capped cylinder/frustum segment between two points.
    """
    pointa = np.asarray(pointa, dtype=np.float64)
    pointb = np.asarray(pointb, dtype=np.float64)
    axis_vec = pointb - pointa
    length = np.linalg.norm(axis_vec)
    axis_dir = axis_vec / length

    arbitrary = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(axis_dir, arbitrary)) > 0.9:
        arbitrary = np.array([0.0, 1.0, 0.0])
    u = np.cross(axis_dir, arbitrary)
    u /= np.linalg.norm(u)
    v = np.cross(axis_dir, u)

    theta = np.linspace(0, 2 * np.pi, n_sides, endpoint=False)
    ring_dirs = np.outer(np.cos(theta), u) + np.outer(np.sin(theta), v)

    ring_a = pointa + ring_dirs * radius_a
    ring_b = pointb + ring_dirs * radius_b

    lateral_normal = ring_dirs * length - (radius_b - radius_a) * axis_dir
    lateral_normal /= np.linalg.norm(lateral_normal, axis=1, keepdims=True)

    points = [ring_a, ring_b]
    normals = [lateral_normal, lateral_normal]
    faces = []
    for i in range(n_sides):
        j = (i + 1) % n_sides
        faces.append((4, i, j, n_sides + j, n_sides + i))

    next_idx = 2 * n_sides

    if cap_a:
        points.append(ring_a)
        normals.append(np.tile(-axis_dir, (n_sides, 1)))
        faces.append((n_sides, *range(next_idx, next_idx + n_sides)))
        next_idx += n_sides
    if cap_b:
        points.append(ring_b)
        normals.append(np.tile(axis_dir, (n_sides, 1)))
        faces.append((n_sides, *range(next_idx, next_idx + n_sides)))
        next_idx += n_sides

    return np.vstack(points), faces, np.vstack(normals)


def load_neuroml_model(filename):
    """Read a NeuroML file (including any included files) into a document that
    can be passed (any number of times) to add_neuroml_model()."""
    nml_doc = pynml.read_neuroml2_file(filename, include_includes=True)
    print("Loaded NeuroML file: %s" % filename)
    return nml_doc


def _build_cell_mesh(cell, rotation, factor, somas_only):
    """The mesh of a single Cell, in the viewer's (rotated/scaled) frame"""
    # accumulate every cylinder/frustum segment's raw geometry here
    # and build a single PolyData for the whole cell below, rather
    # than one pv.PolyData()/merge() per segment (each is a VTK
    # filter call whose fixed overhead dominates for a mesh this
    # small -- see make_segment's docstring). Spheres (zero-length
    # somas) are cheap and few (usually one per cell), so they are
    # kept as separate pieces and merged in once at the end.
    all_points = []
    all_normals = []
    all_faces = []
    offset = 0
    sphere_pieces = []

    for seg in cell.morphology.segments:
        p = cell.get_actual_proximal(seg.id)
        d = seg.distal

        if somas_only and seg.id != 0:
            continue

        pointa = tuple(_transform((p.x, p.y, p.z), rotation, factor))
        pointb = tuple(_transform((d.x, d.y, d.z), rotation, factor))

        if cell.get_segment_length(seg.id) == 0:
            sphere_pieces.append(make_sphere(pointa, p.diameter * factor / 2))
        else:
            pts, faces, normals = make_segment(
                pointa,
                pointb,
                p.diameter * factor / 2,
                d.diameter * factor / 2,
                n_sides=15,
            )
            all_points.append(pts)
            all_normals.append(normals)
            for face in faces:
                all_faces.append((face[0], *(idx + offset for idx in face[1:])))
            offset += len(pts)

    pieces = []
    if all_points:
        seg_mesh = pv.PolyData(np.vstack(all_points), np.hstack(all_faces))
        seg_mesh.point_data.active_normals = np.vstack(all_normals).astype(np.float32)
        pieces.append(seg_mesh)
    pieces.extend(sphere_pieces)

    # one template mesh per cell type, stamped at every instance position
    # via a glyph filter instead of copying/translating it per instance.
    # merge_points=False keeps each segment's own normals distinct at
    # the joints instead of blending them together.
    cell_mesh = (
        pieces[0].merge(pieces[1:], merge_points=False)
        if len(pieces) > 1
        else pieces[0]
    )
    return cell_mesh


def _get_cell_mesh(nml_doc, cell, rotation, factor, somas_only, rotate_xyz):
    """_build_cell_mesh(), kept on the loaded document: building the geometry is
    the slow part of adding a model and only depends on the cell and the
    factor/rotation/somas_only, not on which cells are shown or their color, so
    repeated adds (e.g. a Streamlit rerun) reuse it. Glyphing it at the
    instance positions copies it, so the stored mesh is never modified."""
    cache = nml_doc.__dict__.setdefault("_worm3d_cell_meshes", {})
    key = (cell.id, factor, rotate_xyz, somas_only)
    if key not in cache:
        cache[key] = _build_cell_mesh(cell, rotation, factor, somas_only)
    return cache[key]


def add_neuroml_model(
    plotter,
    nml_doc,
    somas_only=False,
    factor=1,
    rotate_x=0.0,
    rotate_y=0.0,
    rotate_z=0.0,
    only_show=[],
    colors={},
):
    """Add the populations/cells of a loaded NeuroML document to the plotter.

    nml_doc: a NeuroML document, e.g. from load_neuroml_model(). It is not
    modified, so a single loaded document can be reused for many plotters.

    only_show: list of population ids (cell names, e.g. "ADAL") to show; all
    other populations are omitted. An empty list shows everything.

    colors: dict of population id (cell name) -> color (e.g. an rgb tuple) to
    use instead of the color from the model. Cells not in the dict (or an
    empty dict) use the model's color.
    """
    (
        cell_id_vs_cell,
        pop_id_vs_cell,
        positions,
        pop_id_vs_color,
        pop_id_vs_radii,
    ) = extract_position_info(nml_doc, False)

    rotation = _rotation_matrix(rotate_x, rotate_y, rotate_z)

    for pop_id, cell in pop_id_vs_cell.items():
        if only_show and pop_id not in only_show:
            continue

        pos_pop = positions[pop_id]  # type: typing.Dict[typing.Any, typing.List[float]]

        print("Pop: %s has %i of component %s" % (pop_id, len(pos_pop), cell.id))

        radius = pop_id_vs_radii[pop_id] if pop_id in pop_id_vs_radii else 0.5

        # color: given in colors, else set in the model, else a random rgb color
        if pop_id in colors:
            color = colors[pop_id]
        elif pop_id in pop_id_vs_color:
            color = pop_id_vs_color[pop_id]
        else:
            color = np.random.rand(3)

        # instance positions of this population, rotated/scaled to viewer axes
        raw_positions = np.array(list(pos_pop.values()), dtype=float)
        points = _transform(raw_positions, rotation, factor)
        point_cloud = pv.PolyData(points)

        if isinstance(cell, Cell):
            print(
                "Adding a cell with %i segments, which will be added %i time(s)"
                % (len(cell.morphology.segments), len(points))
            )

            cell_mesh = _get_cell_mesh(
                nml_doc,
                cell,
                rotation,
                factor,
                somas_only,
                (rotate_x, rotate_y, rotate_z),
            )
            glyphs = point_cloud.glyph(geom=cell_mesh, scale=False, orient=False)
            plotter.add_mesh(glyphs, color=color, smooth_shading=True)

        else:
            sphere = make_sphere((0.0, 0.0, 0.0), radius)
            glyphs = point_cloud.glyph(geom=sphere, scale=False, orient=False)
            plotter.add_mesh(glyphs, color=color)


if __name__ == "__main__":
    plotter = pv.Plotter()

    c302_nml = "NeuroML2/c302_D_Full.net.nml"

    show_gui = True
    rotate_x = 0

    if "-nogui" in sys.argv:
        show_gui = False
        sys.argv.remove("-nogui")

    if len(sys.argv) > 1 and (
        sys.argv[1].endswith(".nml") or sys.argv[1].endswith(".nml.h5")
    ):
        nml_file = sys.argv[1]
    else:
        nml_file = c302_nml
        rotate_x = -90

    add_neuroml_model(plotter, load_neuroml_model(nml_file), somas_only=False)
    plotter.set_background("white")
    plotter.add_axes()

    plotter.camera_position = "xy"
    plotter.camera.roll = 0
    plotter.camera.elevation = 5

    if show_gui:
        plotter.show()
