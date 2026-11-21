"""PyVista viewer for the adult cell STL meshes of Witvliet et al. (2021), in
the folder Witvliet2021 (get them with ./download_witvliet2021.sh; see
Witvliet2021/README.md).

Every file NAME-SEM_adult.stl (e.g. ADAL-SEM_adult.stl for ADAL) is loaded and
plotted. Known neurons get a color of their own; all the other cells (body wall
muscles, glia, ...) are white. Click a cell to show its name.

As with the other models: load_stl_neurons() reads the meshes once, and
add_stl_neurons() adds (some of) them to a plotter, any number of times.

Usage:
    python witvliet2021.py [models_dir [decimate_fraction]] [-nogui]
    python witvliet2021.py -cache     make the mesh cache used by the Streamlit app
"""

import glob
import os
import sys
import zlib

import numpy as np
import pyvista as pv

import cect.Cells as cells

from meshcache import load_meshes, save_meshes
from neuromlmodel import _rotation_matrix

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "Witvliet2021")
SUFFIX = "-SEM_adult.stl"

# The mesh cache (see meshcache.py) is made with this fraction of the triangles
# removed: the full meshes have ~5 million points, too slow to show in a browser
CACHE_DECIMATE = 0.8
CACHE_NAME = "witvliet2021"


def print_(msg, print_it=True):  # print_it=False when not verbose
    if print_it:
        pre = "Witvliet2021 >>> "
        print("%s %s" % (pre, msg.replace("\n", "\n" + pre)))


def find_stl_files(models_dir=DEFAULT_DIR):
    """dict of cell name -> STL file, for files named NAME-SEM_adult.stl"""
    files = {}
    for path in sorted(glob.glob(os.path.join(models_dir, "*" + SUFFIX))):
        files[os.path.basename(path)[: -len(SUFFIX)]] = path
    return files


def load_stl_neurons(models_dir=DEFAULT_DIR, decimate=0.0, use_cache=False):
    """Read the cell STL files, for add_stl_neurons(). Returns a dict of
    cell name -> pv.PolyData (in the files' own coordinates, float32).

    decimate: fraction of the triangles to remove from each mesh (0 = keep all,
    0.8 = keep 20%). The full resolution meshes have about 5 million points in
    all, much more than is needed (or fast enough) for viewing the whole worm
    in a browser.

    use_cache: read the (much faster) cache made by -cache instead, which has
    the CACHE_DECIMATE decimation, ignoring models_dir and decimate. Raises
    meshcache.CacheError if it hasn't been made."""
    if use_cache:
        return dict(load_meshes(CACHE_NAME)[0])

    files = find_stl_files(models_dir)
    if not files:
        print_(
            "WARNING: no *%s files in %s; run ./download_witvliet2021.sh"
            % (SUFFIX, models_dir)
        )
    print_("Loading %i cell STL files from %s..." % (len(files), models_dir))
    meshes = {}
    for name, path in files.items():
        mesh = pv.read(path)
        if decimate > 0:
            mesh = mesh.decimate(decimate)
        mesh.points = mesh.points.astype(np.float32)
        meshes[name] = mesh
    return meshes


def build_cache(models_dir=DEFAULT_DIR, decimate=CACHE_DECIMATE):
    """Make the mesh cache: the decimated meshes of all the cells"""
    meshes = load_stl_neurons(models_dir, decimate=decimate)
    save_meshes(CACHE_NAME, list(meshes.items()))


def default_color(name):
    """White for cells that are not known neurons (muscles, fragments, ...),
    otherwise a color for the neuron that is the same on every run"""
    if not cells.is_any_neuron(name):
        return "white"
    return tuple(np.random.default_rng(zlib.crc32(("stl:" + name).encode())).random(3))


def stl_center(meshes):
    """Center of the bounding box of all the meshes"""
    bounds = np.array([m.bounds for m in meshes.values()])
    return (bounds[:, 0::2].min(axis=0) + bounds[:, 1::2].max(axis=0)) / 2


def add_stl_neurons(
    plotter,
    meshes,
    scale=1,
    translate=(0, 0, 0),
    rotate_x=0.0,
    rotate_y=0.0,
    rotate_z=0.0,
    only_show=[],
    colors={},
    highlight=[],
    faded_opacity=0.05,
    center=True,
):
    """Add (some of) the cells from load_stl_neurons() to the plotter.

    rotate_x, rotate_y, rotate_z: rotation in degrees about the x, y, then z
    axis (as for add_neuroml_model()), around the middle of the loaded cells
    when center is True, otherwise around the origin.

    only_show: list of cell names (e.g. "AVAL") to show; all others are
    omitted. An empty list shows everything.

    colors: dict of cell name -> color to use instead of the default one.

    highlight: list of cell names to highlight. If not empty, these are shown as
    normal and all the other shown cells are made transparent (opacity
    faded_opacity).

    center: move the middle of all the loaded neurons (not just the shown
    ones, so a subset stays in place) to the origin before translating.

    meshes are not modified. Returns a dict of {name: Actor}.
    """
    translate = np.asarray(translate, dtype=np.float32)
    rotation = _rotation_matrix(rotate_x, rotate_y, rotate_z)
    origin = stl_center(meshes) if center and meshes else np.zeros(3)
    actors = {}
    for name, stl_mesh in meshes.items():
        if only_show and name not in only_show:
            continue
        # a new mesh, so the loaded ones can be reused for other plotters
        points = ((stl_mesh.points - origin) @ rotation.T * scale + translate).astype(
            np.float32
        )
        mesh = pv.PolyData(points, stl_mesh.faces)
        color = colors.get(name)
        if color is None:
            color = default_color(name)
        faded = highlight and name not in highlight
        actor = plotter.add_mesh(
            mesh,
            color=color,
            opacity=faded_opacity if faded else 1.0,
            smooth_shading=True,
        )
        actor.name = name
        actors[name] = actor
    return actors


if __name__ == "__main__":
    show_gui = True
    if "-nogui" in sys.argv:
        show_gui = False
        sys.argv.remove("-nogui")

    if "-cache" in sys.argv:
        build_cache()
        sys.exit(0)

    models_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR

    # python witvliet2021.py [models_dir] [decimate_fraction]
    decimate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    meshes = load_stl_neurons(models_dir, decimate=decimate)

    plotter = pv.Plotter()
    actors = add_stl_neurons(plotter, meshes)
    print_(
        "Plotted %i cells, %i points in total"
        % (len(actors), sum(m.n_points for m in meshes.values()))
    )

    plotter.set_background("white")
    plotter.add_axes()

    def show_picked_name(actor):
        """Print the name of the clicked cell and show it on the canvas"""
        name = actor.name
        kind = "neuron" if cells.is_any_neuron(name) else "cell"
        print_("Picked %s: %s" % (kind, name))
        # a fixed name, so each click replaces the previous label
        plotter.add_text(
            name, position="upper_left", font_size=16, color="black", name="picked"
        )

    plotter.enable_mesh_picking(
        callback=show_picked_name,
        use_actor=True,
        left_clicking=True,
        show_message=False,
    )
    plotter.add_text(
        "Click a cell to show its name",
        position="lower_left",
        font_size=9,
        color="gray",
    )

    if show_gui:
        plotter.show()
