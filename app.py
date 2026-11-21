from meshcache import CacheError
from neuromlmodel import add_neuroml_meshes, load_neuroml_cache  # noqa: F401
from SiberneticReplay import add_sibernetic_model  # noqa: F401
from witvliet2021 import add_stl_neurons, load_stl_neurons  # noqa: F401
from virtualworm import add_virtualworm_muscles, load_virtualworm_muscles  # noqa: F401
from virtualworm import add_virtualworm_neurons, load_virtualworm_neurons  # noqa: F401

import os
import platform
import shutil
import subprocess
import sys
import zlib

import numpy as np

import pyvista as pv

version = "v0.3.5"

stpyvista_version = "0.1.4"

st_mode = "-gui" not in sys.argv


def print_(msg, print_it=True):  # print_it=False when not verbose
    if print_it:
        pre = "Worm3DViewer >>> "
        print("%s %s" % (pre, msg.replace("\n", "\n" + pre)))


def start_xvfb(display=99, resolution=(1024, 768)):
    """Start a virtual X server for headless rendering.

    Replacement for stpyvista.utils.start_xvfb (removed in stpyvista>=0.2) and
    pyvista.start_xvfb (removed in recent pyvista). Only needed on Linux with no
    display, e.g. in the Docker image.
    """
    if platform.system() != "Linux" or os.environ.get("DISPLAY"):
        return
    if shutil.which("Xvfb") is None:
        print_("Xvfb not found; assuming offscreen rendering is available")
        return
    subprocess.Popen(
        ["Xvfb", f":{display}", "-screen", "0", "%dx%dx24" % resolution],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.environ["DISPLAY"] = f":{display}"


print_("Starting OpenWorm 3D Viewer (%s)" % version)

if st_mode:
    import streamlit as st

    print_("Streamlit mode detected...")

    st.set_page_config(layout="wide")

    if "IS_XVFB_RUNNING" not in st.session_state:
        print_("Starting XVFB...")
        start_xvfb()
        st.session_state.IS_XVFB_RUNNING = True

    # Compact, OpenWorm Browser-like look: green page, small text, tight spacing
    st.markdown(
        """
<style>
:root { --ow-green: #9dbe45; --ow-dark: #4c6a22; --ow-text: #2c4310; }
header[data-testid="stHeader"] { display: none; }
.stApp { background: var(--ow-green); }
.block-container { padding: 0.6rem 1rem 2.6rem 1rem; max-width: 100%; }
div[data-testid="stVerticalBlock"] { gap: 0.35rem; }
div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
.stApp p.ow-title { color: #fff; font-size: 1.25rem; font-weight: 600; margin: 0;
            line-height: 1.5; text-shadow: 0 1px 2px rgba(0,0,0,0.25); }
.ow-title span { font-size: 0.75rem; font-weight: 400; margin-left: 0.6rem;
                 opacity: 0.9; }
.stApp p, .stApp label, .stApp [data-testid="stWidgetLabel"] p {
  font-size: 0.78rem; margin: 0; color: var(--ow-text); }
div[data-testid="stCheckbox"] { min-height: 0; }
div[data-testid="stCheckbox"] label { gap: 0.3rem; }
div[data-testid="stSelectbox"] > div, div[data-testid="stMultiSelect"] > div {
  font-size: 0.78rem; }
div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  min-height: 1.9rem; background: rgba(255,255,255,0.75); border-radius: 1rem; }
/* The panel box: the inner block of the bordered layout wrapper in a column */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
  > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"] {
  background: rgba(255,255,255,0.22); border-color: rgba(44,67,16,0.35);
  border-radius: 0.6rem; }
/* Space below the page title, before the panels */
div[data-testid="stElementContainer"]:has(.ow-title) { margin-bottom: 0.7rem; }
/* Equal height panels: each column fills its row, and the bordered panel
   (a layout wrapper directly in a column) fills the column */
div[data-testid="stColumn"] { display: flex; flex-direction: column; }
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] { flex: 1 1 auto; }
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
  > div[data-testid="stLayoutWrapper"] { flex: 1 1 auto; }
.ow-panel-title { font-size: 0.68rem !important; font-weight: 700;
                  text-transform: uppercase; letter-spacing: 0.06em;
                  color: var(--ow-dark) !important; margin: 0;
                  line-height: 1.4; margin-bottom: 0.8rem !important; }
.ow-footer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 999;
             background: var(--ow-dark); color: #fff; font-size: 0.72rem;
             padding: 0.35rem 1rem; text-align: right; }
.ow-footer a { color: var(--ow-green); text-decoration: none; }
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="ow-title">OpenWorm 3D Viewer<span> 3D viewer'
        " for <i>C. elegans</i> models and datasets</span></p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ow-footer">OpenWorm 3D Viewer %s &middot; pyvista v%s, '
        "stpyvista v%s, streamlit v%s</div>"
        % (version, pv.__version__, stpyvista_version, st.__version__),
        unsafe_allow_html=True,
    )

## Default selection of models to show (the checkboxes below override these
## in Streamlit mode)
adding_sibernetic_model = False
adding_neuroml_model = False
adding_virtualworm_muscles = False
adding_virtualworm_neurons = True
adding_stl_neurons = False


# Default spacing between the worms (the slider in Streamlit mode can lower it)
DEFAULT_SPACING = 50

NEUROML_FILE = "NeuroML2/c302_D_Full.net.nml"

# Scale of the STL neurons, to match the other models
STL_SCALE = 0.33
# Move of the STL cells (x, y, z), after the scaling and rotation, on top of
# their place next to the VirtualWorm models
STL_OFFSET = (0, 8, 52)
# Rotation (degrees about x, y, z) of the STL cells, to match the other models
STL_ROTATE = (270, 90, 0)


# The meshes of the models are read from the mesh caches (made by running the
# loaders with -cache, see meshcache.py; a CacheError is raised if they are
# missing), once, and then kept by Streamlit, so changing the cell selection only
# re-adds cells to a new plotter. They are not modified when adding them to a
# plotter, so sharing is safe.
def _cached(func):
    return st.cache_resource(show_spinner=False)(func) if st_mode else func


@_cached
def get_neuroml_meshes():
    return load_neuroml_cache()


@_cached
def get_virtualworm_muscles():
    return load_virtualworm_muscles(use_cache=True)


@_cached
def get_virtualworm_neurons():
    return load_virtualworm_neurons(use_cache=True)


@_cached
def get_stl_neurons():
    return load_stl_neurons(use_cache=True)


def get_cell_groups(nml_file):
    """Groups of cell names (present in the NeuroML file) to select from.
    An empty list means "all cells"."""
    import re

    import cect.Cells as cells

    with open(nml_file) as f:
        ids = re.findall(r'<population id="([^"]*)"', f.read())

    def present(names):
        return [i for i in ids if i in names]

    return {
        "All cells": [],
        "Only muscles": [i for i in ids if cells.is_known_muscle(i)],
        "Only neurons": [i for i in ids if cells.is_any_neuron(i)],
        "Sensory neurons": present(cells.SENSORY_NEURONS_COOK),
        "Interneurons": present(cells.INTERNEURONS_COOK),
        "Motor neurons": present(cells.MOTORNEURONS_COOK),
        "Pharyngeal neurons": present(cells.PHARYNGEAL_NEURONS),
        "Specific cells...": None,
    }, ids


def build_scene(
    sibernetic,
    neuroml,
    vw_muscles,
    vw_neurons,
    stl_neurons=False,
    only_show=(),
    highlight=(),
    colors={},
    background=None,
    spacing=DEFAULT_SPACING,
):
    """Build a plotter containing the selected models"""
    # Off-screen in Streamlit mode: the script runs on a non-main thread, where
    # on-screen rendering (e.g. Cocoa on macOS) aborts
    plotter = pv.Plotter(window_size=[800, 800], off_screen=st_mode)
    if background:
        plotter.set_background(background)

    if vw_neurons:
        print_("Adding VirtualWorm neurons...")
        add_virtualworm_neurons(
            plotter,
            get_virtualworm_neurons(),
            translate=((-0.8 * spacing - (vw_muscles * spacing)), 0, 0),
            only_show=list(only_show),
            highlight=list(highlight),
            colors=colors,
        )

    if vw_muscles:
        print_("Adding VirtualWorm muscles...")
        add_virtualworm_muscles(
            plotter,
            get_virtualworm_muscles(),
            translate=(-1 * spacing, 0, 0),
            only_show=list(only_show),
            highlight=list(highlight),
            colors=colors,
        )

    if stl_neurons:
        print_("Adding Witvliet et al 2021 cells...")
        # to the left of the VirtualWorm worms
        add_stl_neurons(
            plotter,
            get_stl_neurons(),
            scale=STL_SCALE,
            rotate_x=STL_ROTATE[0],
            rotate_y=STL_ROTATE[1],
            rotate_z=STL_ROTATE[2],
            translate=(
                -(0.8 + vw_muscles + vw_neurons) * 0.8 * spacing + STL_OFFSET[0],
                STL_OFFSET[1],
                STL_OFFSET[2],
            ),
            only_show=list(only_show),
            highlight=list(highlight),
            colors=colors,
        )

    if neuroml:
        print_("Adding NeuroML model...")
        # the scale and rotation of the cells are fixed in the cache
        add_neuroml_meshes(
            plotter,
            *get_neuroml_meshes(),
            only_show=list(only_show),
            highlight=list(highlight),
            colors=colors,
        )  # at 0...

    if sibernetic:
        print_("Adding Sibernetic model...")
        add_sibernetic_model(
            plotter,
            swap_y_z=True,
            offset3d=(spacing, -50, -100),
            show_footprint=False,
            only_show=list(only_show),
            colors=colors,
        )

    plotter.add_axes()  # the xyz axes indicator
    plotter.set_viewup([0, 10, 0])
    return plotter


def random_colors(names):
    """A dict of a random (but repeatable for a given name) rgb color per name"""
    return {
        name: tuple(np.random.default_rng(zlib.crc32(name.encode())).random(3))
        for name in names
    }


RANDOM_OPTION = "Consistent, random colors"
COLOUR_OPTIONS = ["Default", RANDOM_OPTION]  # the first is the default in the UI

# Background of the 3D view; green matches the page (OpenWorm green)
BACKGROUNDS = {"Green": "#9dbe45", "White": "white", "Black": "black"}

only_show = []
highlight = []
colour_option = COLOUR_OPTIONS[0]
background_option = "Green"
spacing = DEFAULT_SPACING


def panel_title(text):
    st.markdown('<p class="ow-panel-title">%s</p>' % text, unsafe_allow_html=True)


if st_mode:
    groups, all_cell_ids = get_cell_groups(NEUROML_FILE)
    # the same groups as for showing, but none highlighted by default ("All cells"
    # highlighted would fade nothing)
    HIGHLIGHT_OPTIONS = ["None"] + [g for g in groups if g != "All cells"]

    # Control panels, in the order they are intended to be used:
    # what to show (Canvas), which cells (Subsets), colours (Overlay), Settings
    p_canvas, p_subsets, p_overlay, p_settings = st.columns([3, 3, 2, 2])

    with p_canvas.container(border=True):
        panel_title("3D Canvas")
        c1, c2 = st.columns(2)
        adding_virtualworm_neurons = c1.checkbox(
            "VirtualWorm neurons", value=adding_virtualworm_neurons, key="cb_vw_neurons"
        )
        adding_virtualworm_muscles = c2.checkbox(
            "VirtualWorm muscles", value=adding_virtualworm_muscles, key="cb_vw_muscles"
        )
        adding_neuroml_model = c1.checkbox(
            "NeuroML model (c302)", value=adding_neuroml_model, key="cb_neuroml"
        )
        adding_sibernetic_model = c2.checkbox(
            "Sibernetic model", value=adding_sibernetic_model, key="cb_sibernetic"
        )
        adding_stl_neurons = c1.checkbox(
            "Witvliet et al 2021 adult cells", value=adding_stl_neurons, key="cb_stl"
        )

    with p_subsets.container(border=True):
        panel_title("Select Subsets")
        show_label, show_col = st.columns([1, 2], vertical_alignment="center")
        show_label.markdown("Show")
        group = show_col.selectbox(
            "Cells to show",
            list(groups.keys()),
            key="sel_cell_group",
            label_visibility="collapsed",
            help="Which cells to show",
        )
        if groups[group] is None:
            only_show = st.multiselect(
                "Choose cells to show:",
                all_cell_ids,
                default=["AVAL", "AVAR"],
                key="sel_cells",
                label_visibility="collapsed",
            )
        else:
            only_show = groups[group]

        hl_label, hl_col = st.columns([1, 2], vertical_alignment="center")
        hl_label.markdown("Highlight")
        hl_group = hl_col.selectbox(
            "Cells to highlight",
            HIGHLIGHT_OPTIONS,
            key="sel_highlight_group",
            label_visibility="collapsed",
            help="Cells to show as normal, with all the other shown cells "
            "made transparent (not yet implemented for Sibernetic)",
        )
        if hl_group == "Specific cells...":
            highlight = st.multiselect(
                "Choose cells to highlight:",
                all_cell_ids,
                key="sel_hl_cells",
                label_visibility="collapsed",
            )
        elif hl_group != "None":
            highlight = groups[hl_group]

    with p_overlay.container(border=True):
        panel_title("Color Overlay")
        colour_option = st.selectbox(
            "Colours to use",
            COLOUR_OPTIONS,
            key="sel_colours",
            label_visibility="collapsed",
            help="Colours to use: Default = those in each loaded model; "
            f"{RANDOM_OPTION} = a random colour for each named cell",
        )

    with p_settings.container(border=True):
        panel_title("Display Options")
        background_option = (
            st.segmented_control(
                "Background",
                list(BACKGROUNDS),
                default="Green",
                key="sel_background",
                label_visibility="collapsed",
                help="Background colour of the 3D view",
            )
            or "Green"  # nothing selected (clicking the active option deselects it)
        )
        label_col, slider_col = st.columns([1, 2], vertical_alignment="center")
        label_col.markdown("Worm spacing")
        spacing = slider_col.slider(
            "Worm spacing",
            min_value=0,
            max_value=DEFAULT_SPACING,
            value=DEFAULT_SPACING,
            key="sel_spacing",
            label_visibility="collapsed",
            help="Distance between the worms: lower values move them closer together",
        )

# Empty dict -> each model uses its own colors
colors = random_colors(all_cell_ids) if colour_option == RANDOM_OPTION else {}

selection = (
    adding_sibernetic_model,
    adding_neuroml_model,
    adding_virtualworm_muscles,
    adding_virtualworm_neurons,
    adding_stl_neurons,
    tuple(only_show),
    tuple(highlight),
    colors,
    BACKGROUNDS[background_option] if st_mode else None,
    spacing,
)

if st_mode:
    try:
        with st.spinner("Loading worm models...", show_time=True):
            plotter = build_scene(*selection)
    except CacheError as e:
        st.error(str(e))
        st.stop()
else:
    plotter = build_scene(*selection)

print_("Created the scene...")

if st_mode:
    ##
    if True:
        print_("Pass a key to avoid re-rendering at each page change")
        from stpyvista import stpyvista

        # The key depends on the selection so the view is re-mounted (and so
        # updated) when a checkbox changes
        view_key = "pv_Sib%d_NML%d_VWM%d_VWN%d_STL%d" % (
            adding_sibernetic_model,
            adding_neuroml_model,
            adding_virtualworm_muscles,
            adding_virtualworm_neurons,
            adding_stl_neurons,
        )
        view_key += "_%d_%d_%s_%s" % (
            hash(tuple(only_show)),
            hash(tuple(highlight)),
            colour_option,
            background_option,
        )
        view_key += "_sp%d" % spacing

        with st.spinner("Displaying worm models...", show_time=True):
            # The panel backend needs no extra dependencies (the default, trame, does)
            stpyvista(plotter, backend="panel", key=view_key)
            # The scene is exported to the browser by now. Close the plotter, as a
            # new one is built on every rerun and would otherwise be left holding
            # its render window and meshes.
            plotter.close()

            print_("Scene rendered in the browser (Streamlit mode).")
    pass
else:
    plotter.show()
