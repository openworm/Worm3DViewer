import numpy as np
import pyvista as pv

import sys

from pyneuroml import pynml
from pyneuroml.utils import extract_position_info
from neuroml import Cell


def make_segment(
    pointa, pointb, radius_a, radius_b, n_sides=15, cap_a=True, cap_b=True
):
    """Build a solid, capped cylinder/frustum segment between two points."""
    pointa = np.array(pointa, dtype=float)
    pointb = np.array(pointb, dtype=float)
    axis_dir = pointb - pointa
    axis_dir = axis_dir / np.linalg.norm(axis_dir)

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

    lateral_faces = []
    for i in range(n_sides):
        j = (i + 1) % n_sides
        lateral_faces.append([4, i, j, n_sides + j, n_sides + i])
    lateral = pv.PolyData(np.vstack([ring_a, ring_b]), np.hstack(lateral_faces))
    lateral.compute_normals(inplace=True, auto_orient_normals=True)

    pieces = [lateral]
    if cap_a:
        cap = pv.PolyData(ring_a, np.hstack([[n_sides, *range(n_sides)]]))
        # must match compute_normals()'s float32 output: merge() silently
        # drops a point-data array if its dtype differs between pieces
        cap.point_data.active_normals = np.tile(-axis_dir, (n_sides, 1)).astype(
            np.float32
        )
        pieces.append(cap)
    if cap_b:
        cap = pv.PolyData(ring_b, np.hstack([[n_sides, *range(n_sides)]]))
        cap.point_data.active_normals = np.tile(axis_dir, (n_sides, 1)).astype(
            np.float32
        )
        pieces.append(cap)

    # merge_points=False: the cap/wall boundary points are intentionally
    # duplicated (see above) so merging must not weld them back together
    return (
        pieces[0].merge(pieces[1:], merge_points=False)
        if len(pieces) > 1
        else pieces[0]
    )


def add_neuroml_model(plotter, filename, somas_only=False, factor=1):

    nml_doc = pynml.read_neuroml2_file(filename, include_includes=True)

    print("Loaded NeuroML file: %s" % filename)

    (
        cell_id_vs_cell,
        pop_id_vs_cell,
        positions,
        pop_id_vs_color,
        pop_id_vs_radii,
    ) = extract_position_info(nml_doc, False)

    for pop_id, cell in pop_id_vs_cell.items():
        pos_pop = positions[pop_id]  # type: typing.Dict[typing.Any, typing.List[float]]

        print("Pop: %s has %i of component %s" % (pop_id, len(pos_pop), cell.id))

        radius = pop_id_vs_radii[pop_id] if pop_id in pop_id_vs_radii else 0.5
        color = pop_id_vs_color[pop_id] if pop_id in pop_id_vs_color else "r"

        # instance positions of this population, remapped/scaled to viewer axes
        points = np.array(
            [
                [pos[0] * factor, pos[2] * factor, -1 * pos[1] * factor]
                for pos in pos_pop.values()
            ]
        )
        point_cloud = pv.PolyData(points)

        if isinstance(cell, Cell):
            print("Loading a cell with %i segments" % len(cell.morphology.segments))

            seg_meshes = []

            for seg in cell.morphology.segments:
                p = cell.get_actual_proximal(seg.id)
                d = seg.distal

                if somas_only and seg.id != 0:
                    continue

                pointa = (p.x * factor, p.z * factor, -1 * p.y * factor)
                pointb = (d.x * factor, d.z * factor, -1 * d.y * factor)

                if cell.get_segment_length(seg.id) == 0:
                    seg_mesh = pv.Sphere(
                        center=pointa,
                        radius=p.diameter * factor / 2,
                    )
                else:
                    seg_mesh = make_segment(
                        pointa,
                        pointb,
                        p.diameter * factor / 2,
                        d.diameter * factor / 2,
                        n_sides=15,
                    )

                seg_meshes.append(seg_mesh)

            # one template mesh per cell type, stamped at every instance position
            # via a glyph filter instead of copying/translating it per instance.
            # merge_points=False keeps each segment's own normals distinct at
            # the joints instead of blending them together.
            cell_mesh = (
                seg_meshes[0].merge(seg_meshes[1:], merge_points=False)
                if len(seg_meshes) > 1
                else seg_meshes[0]
            )
            glyphs = point_cloud.glyph(geom=cell_mesh, scale=False, orient=False)
            plotter.add_mesh(glyphs, color=color, smooth_shading=True)

        else:
            sphere = pv.Sphere(radius=radius)
            glyphs = point_cloud.glyph(geom=sphere, scale=False, orient=False)
            plotter.add_mesh(glyphs, color=color)


if __name__ == "__main__":
    plotter = pv.Plotter()

    c302_nml = "NeuroML2/c302_D_Full.net.nml"

    show_gui = True
    if "-nogui" in sys.argv:
        show_gui = False
        sys.argv.remove("-nogui")

    if len(sys.argv) > 1 and sys.argv[1].endswith(".nml"):
        nml_file = sys.argv[1]
    else:
        nml_file = c302_nml

    add_neuroml_model(plotter, nml_file, somas_only=False)
    plotter.set_background("white")
    plotter.add_axes()

    if show_gui:
        plotter.show()
