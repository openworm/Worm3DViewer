import numpy as np
import pyvista as pv
import trimesh

from cect.Cells import is_known_cell, cell_notes

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


def add_named_objects(plotter, obj_file, scale=20, translate=(0, 0, 0), **mesh_kwargs):
    """Load obj_file preserving its named `o object_name` groups, adding
    each as its own actor (keyed by that name) instead of merging
    everything into one mesh -- so individual objects can be shown/hidden
    later via plotter.actors[name].visibility = False/True.

    pv.read() (VTK's OBJ reader) both merges every `o` group into a
    single mesh, discarding the names, and doesn't weld shared vertices
    between face corners, so it also uses ~4x the points a properly
    indexed mesh needs. trimesh preserves the named groups and reads
    vertices as actually indexed in the file.

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

    Returns a dict of {name: Actor}.
    """
    scene = trimesh.load(
        obj_file, process=False, group_material=False, split_object=True
    )
    translate = np.asarray(translate)
    actors = {}
    for name, geom in scene.geometry.items():
        mesh = pv.wrap(geom)
        mesh.points = mesh.points * scale + translate
        new_name = standardise_name(name)
        actor = plotter.add_mesh(
            mesh, color=get_color_for_object(new_name), **mesh_kwargs
        )
        actor.name = new_name
        actors[new_name] = actor
    return actors


def add_virtualworm_muscles(plotter, scale=20, translate=(-40, 0, 0)):
    print("Adding virtual worm file %s..." % BODY_WALL_MUSCLE_OBJ_FILE)
    return add_named_objects(
        plotter,
        BODY_WALL_MUSCLE_OBJ_FILE,
        scale=scale,
        translate=translate,
        smooth_shading=True,
    )


def add_virtualworm_neurons(plotter, scale=20, translate=(-80, 0, 0)):
    print("Adding virtual worm file %s..." % NEURONS_OBJ_FILE)
    return add_named_objects(
        plotter,
        NEURONS_OBJ_FILE,
        scale=scale,
        translate=translate,
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
