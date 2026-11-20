import numpy as np
import pyvista as pv

from cect.Cells import is_known_cell, cell_notes

import re
import sys

BODY_WALL_MUSCLE_OBJ_FILE = "bwm.obj"
NEURONS_OBJ_FILE = "neurons.obj"

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


def read_obj_objects(obj_file, only_show=[]):
    """Yield (standardised name, pv.PolyData) for each `o` object in obj_file.

    This parses the file directly instead of using trimesh: with trimesh 5.x
    split_object=True gives every object the name of the first one (ALNR,
    ALNR_1, ...) so the real cell names are lost. In these files each object
    has its own `v` lines, while `f` indices are global to the file.

    If only_show is not empty, objects whose name (or base name, see
    _base_name) is not in it are skipped without being parsed.
    """
    with open(obj_file, "rb") as f:
        data = f.read()

    blocks = data.split(b"\no ")
    n_vertices_before = blocks[0].count(b"\nv ") + blocks[0].startswith(b"v ")

    for block in blocks[1:]:
        n_v = block.count(b"\nv ")
        offset = n_vertices_before
        n_vertices_before += n_v

        lines = block.split(b"\n")
        name = standardise_name(lines[0].decode())
        if only_show and _base_name(name) not in only_show and name not in only_show:
            continue

        points = np.array(
            b" ".join(ln[2:] for ln in lines if ln.startswith(b"v ")).split(),
            dtype=float,
        ).reshape(-1, 3)

        tris = []
        for ln in lines:
            if ln.startswith(b"f "):
                idx = [int(t.split(b"/")[0]) - 1 - offset for t in ln.split()[1:]]
                for i in range(1, len(idx) - 1):  # fan triangulation
                    tris.append((3, idx[0], idx[i], idx[i + 1]))

        yield name, pv.PolyData(points, np.array(tris, dtype=np.int64).ravel())


def add_named_objects(
    plotter, obj_file, scale=20, translate=(0, 0, 0), only_show=[], **mesh_kwargs
):
    """Load obj_file preserving its named `o object_name` groups, adding
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

    Returns a dict of {name: Actor}.
    """
    translate = np.asarray(translate)
    actors = {}
    for name, mesh in read_obj_objects(obj_file, only_show=only_show):
        mesh.points = mesh.points * scale + translate
        actor = plotter.add_mesh(mesh, color=get_color_for_object(name), **mesh_kwargs)
        actor.name = name
        actors[name] = actor
    return actors


def add_virtualworm_muscles(plotter, scale=20, translate=(-40, 0, 0), only_show=[]):
    print("Adding virtual worm file %s..." % BODY_WALL_MUSCLE_OBJ_FILE)
    return add_named_objects(
        plotter,
        BODY_WALL_MUSCLE_OBJ_FILE,
        scale=scale,
        translate=translate,
        only_show=only_show,
        smooth_shading=True,
    )


def add_virtualworm_neurons(plotter, scale=20, translate=(-80, 0, 0), only_show=[]):
    print("Adding virtual worm file %s..." % NEURONS_OBJ_FILE)
    return add_named_objects(
        plotter,
        NEURONS_OBJ_FILE,
        scale=scale,
        translate=translate,
        only_show=only_show,
        smooth_shading=True,
    )


def print_picked_name(actor):
    cell = actor.name
    print(
        "Picked cell: %s (%s)"
        % (cell, cell_notes[cell] if cell in cell_notes else "Unknown cell!")
    )


if __name__ == "__main__":
    pl = pv.Plotter()

    add_virtualworm_muscles(pl)
    add_virtualworm_neurons(pl)

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
