import numpy as np
import pyvista as pv

from cect.Cells import is_known_cell, cell_notes

from meshcache import load_meshes, save_meshes

import re
import sys

BODY_WALL_MUSCLE_OBJ_FILE = "bwm.obj"
NEURONS_OBJ_FILE = "neurons.obj"

# Names of the mesh caches (see meshcache.py)
MUSCLES_CACHE = "virtualworm_muscles"
NEURONS_CACHE = "virtualworm_neurons"

cell_mappings = {
    "Excretory_Cell": "exc_cell",
    "Excretory_Gland_Cell": "exc_gl",
    "Head_Mesodermal_Cell": "hmc",
}

unrecognised_cells = [
    "Excretory_Pore_Cell",
    "Excretory_Duct_Cell",
    "ccPR",
    "ccAR",
    "ccAL",
    "ccPL",
    "ccDL",
    "ccDR",
]


def standardise_name(name):
    new_name = name.strip()

    if new_name.startswith("mu_bod_"):
        part = new_name[7:].upper()
        if len(part) == 3:
            part = part[:2] + "0" + part[2:]
        new_name = "M" + part
    elif name in cell_mappings:
        new_name = cell_mappings[name]

    print("Translated name '%s' -> '%s'" % (name, new_name))
    # assert(is_known_cell(new_name) or new_name in unrecognised_cells), f"Unrecognised C. elegans cell name: {new_name} (was: {name})"
    if not (is_known_cell(new_name) or new_name in unrecognised_cells):
        print(f"WARNING: Unrecognised C. elegans cell name: {new_name} (was: {name})")
    return new_name


def get_color_for_object(name):
    """Pick a display color for a named object: body wall muscles
    (name starting with "mu_bod") are green; everything else gets a
    random color."""
    if name.startswith("M"):
        return "green"
    return np.random.rand(3)


def _base_name(name):
    """A cell can be split over several objects, e.g. ALNR_1, MVL22_81"""
    return re.sub(r"_\d+$", "", name)


def read_obj_objects(obj_file):
    """Return a list of (standardised name, pv.PolyData) for each `o` object in
    obj_file.

    This parses the file directly instead of using trimesh: with trimesh 5.x
    split_object=True gives every object the name of the first one (ALNR,
    ALNR_1, ...) so the real cell names are lost. In these files each object
    has its own `v` lines, while `f` indices are global to the file.

    The meshes are in the file's own coordinates (they are not scaled or
    moved), so the result can be kept and passed to add_named_objects() many
    times.
    """
    with open(obj_file, "rb") as f:
        data = f.read()

    blocks = data.split(b"\no ")
    n_vertices_before = blocks[0].count(b"\nv ") + blocks[0].startswith(b"v ")

    objects = []
    for block in blocks[1:]:
        n_v = block.count(b"\nv ")
        offset = n_vertices_before
        n_vertices_before += n_v

        lines = block.split(b"\n")
        name = standardise_name(lines[0].decode())

        points = np.array(
            b" ".join(ln[2:] for ln in lines if ln.startswith(b"v ")).split(),
            dtype=np.float32,  # half the memory (and size sent to the browser)
        ).reshape(-1, 3)

        tris = []
        for ln in lines:
            if ln.startswith(b"f "):
                idx = [int(t.split(b"/")[0]) - 1 - offset for t in ln.split()[1:]]
                for i in range(1, len(idx) - 1):  # fan triangulation
                    tris.append((3, idx[0], idx[i], idx[i + 1]))

        objects.append(
            (name, pv.PolyData(points, np.array(tris, dtype=np.int64).ravel()))
        )
    return objects


def add_named_objects(
    plotter,
    objects,
    scale=20,
    translate=(0, 0, 0),
    only_show=[],
    colors={},
    highlight=[],
    faded_opacity=0.1,
    **mesh_kwargs,
):
    """Add objects (from read_obj_objects()) preserving their names, adding
    each as its own actor (keyed by that name) instead of merging
    everything into one mesh -- so individual objects can be shown/hidden
    later via plotter.actors[name].visibility = False/True.

    pv.read() (VTK's OBJ reader) both merges every `o` group into a
    single mesh, discarding the names, and doesn't weld shared vertices
    between face corners, so it also uses ~4x the points a properly
    indexed mesh needs. read_obj_objects parses the file itself, keeping the named groups and
    the vertices as actually indexed in the file.

    add_mesh(..., name=name) is deliberately avoided: passing a name
    makes it call remove_actor(name) first, to replace any existing
    actor with that name, and that scan is O(current actor count) --
    for hundreds of guaranteed-unique names added in a loop, that makes
    the whole load O(n^2). plotter.actors[name] resolves by reading
    each actor's .name attribute directly off the live VTK collection
    (there's no separate name index to keep in sync), so setting
    actor.name after creation is just as functional and skips that scan.

    mesh.scale()/mesh.translate() are also avoided: each runs its own
    vtkTransformFilter pipeline, so that's two more filter calls per
    object. scale() scales from the origin by default, so the combined
    effect of both is just points * scale + translate -- one numpy op
    instead of two filter executions.

    only_show: list of (standardised) cell names to show, e.g. "AVAL" or
    "MDL01" (including all numbered parts of that cell); all other objects
    are omitted. An empty list shows everything.

    colors: dict of cell name -> color to use instead of the default color for
    that object (a cell's numbered parts, e.g. MVL22_81, use the color of MVL22).
    Cells not in the dict (or an empty dict) get the default color.

    highlight: list of cell names to highlight. If not empty, these are shown
    as normal and all the other shown objects are made transparent (opacity
    faded_opacity). An empty list highlights nothing (all are opaque).

    objects are not modified.

    Returns a dict of {name: Actor}.
    """
    translate = np.asarray(translate, dtype=np.float32)
    actors = {}
    for name, obj_mesh in objects:
        if only_show and _base_name(name) not in only_show and name not in only_show:
            continue
        # a new mesh, so the loaded objects can be reused for other plotters
        mesh = pv.PolyData(obj_mesh.points * scale + translate, obj_mesh.faces)
        color = colors.get(name, colors.get(_base_name(name)))
        if color is None:
            color = get_color_for_object(name)
        faded = (
            highlight and _base_name(name) not in highlight and name not in highlight
        )
        actor = plotter.add_mesh(
            mesh, color=color, opacity=faded_opacity if faded else 1.0, **mesh_kwargs
        )
        actor.name = name
        actors[name] = actor
    return actors


def load_virtualworm_muscles(use_cache=False):
    """Read the VirtualWorm muscles mesh file, for add_virtualworm_muscles().
    use_cache: read the (much faster) cache made by -cache instead, which
    raises meshcache.CacheError if it hasn't been made."""
    if use_cache:
        return load_meshes(MUSCLES_CACHE)[0]
    print("Loading virtual worm file %s..." % BODY_WALL_MUSCLE_OBJ_FILE)
    return read_obj_objects(BODY_WALL_MUSCLE_OBJ_FILE)


def add_virtualworm_muscles(
    plotter,
    objects,
    scale=20,
    translate=(-40, 0, 0),
    only_show=[],
    colors={},
    highlight=[],
):
    """Add (some of) the objects from load_virtualworm_muscles() to the plotter"""
    print("Adding virtual worm muscles...")
    return add_named_objects(
        plotter,
        objects,
        scale=scale,
        translate=translate,
        only_show=only_show,
        colors=colors,
        highlight=highlight,
        smooth_shading=True,
    )


def load_virtualworm_neurons(use_cache=False):
    """Read the VirtualWorm neurons mesh file, for add_virtualworm_neurons().
    use_cache: as for load_virtualworm_muscles()"""
    if use_cache:
        return load_meshes(NEURONS_CACHE)[0]
    print("Loading virtual worm file %s..." % NEURONS_OBJ_FILE)
    return read_obj_objects(NEURONS_OBJ_FILE)


def build_cache():
    """Make the mesh caches of the muscles and the neurons"""
    save_meshes(MUSCLES_CACHE, load_virtualworm_muscles())
    save_meshes(NEURONS_CACHE, load_virtualworm_neurons())


def add_virtualworm_neurons(
    plotter,
    objects,
    scale=20,
    translate=(-80, 0, 0),
    only_show=[],
    colors={},
    highlight=[],
):
    """Add (some of) the objects from load_virtualworm_neurons() to the plotter"""
    print("Adding virtual worm neurons...")
    return add_named_objects(
        plotter,
        objects,
        scale=scale,
        translate=translate,
        only_show=only_show,
        colors=colors,
        highlight=highlight,
        smooth_shading=True,
    )


def print_picked_name(actor):
    cell = actor.name
    print(
        "Picked cell: %s (%s)"
        % (cell, cell_notes[cell] if cell in cell_notes else "Unknown cell!")
    )


if __name__ == "__main__":
    if "-cache" in sys.argv:
        build_cache()
        sys.exit(0)

    pl = pv.Plotter()

    add_virtualworm_muscles(pl, load_virtualworm_muscles())
    add_virtualworm_neurons(pl, load_virtualworm_neurons())

    pl.enable_mesh_picking(
        callback=print_picked_name,
        use_actor=True,
        left_clicking=True,
        show_message=False,
    )

    pl.set_background("white")
    pl.add_axes()

    if "-nogui" not in sys.argv:
        pl.show()
