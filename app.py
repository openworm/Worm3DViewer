from neuromlmodel import add_neuroml_model, load_neuroml_model  # noqa: F401
from SiberneticReplay import add_sibernetic_model  # noqa: F401
from virtualworm import add_virtualworm_muscles  # noqa: F401
from virtualworm import add_virtualworm_neurons  # noqa: F401

import os
import platform
import shutil
import subprocess
import sys

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
.ow-title { color: #fff; font-size: 1.25rem; font-weight: 600; margin: 0;
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
adding_neuroml_model = True
adding_virtualworm_muscles = False
adding_virtualworm_neurons = False

if st_mode:
    cols = st.columns(4)
    adding_virtualworm_neurons = cols[0].checkbox(
        "VirtualWorm neurons", value=adding_virtualworm_neurons, key="cb_vw_neurons"
    )
    adding_virtualworm_muscles = cols[1].checkbox(
        "VirtualWorm muscles", value=adding_virtualworm_muscles, key="cb_vw_muscles"
    )
    adding_neuroml_model = cols[2].checkbox(
        "NeuroML model (c302)", value=adding_neuroml_model, key="cb_neuroml"
    )
    adding_sibernetic_model = cols[3].checkbox(
        "Sibernetic model", value=adding_sibernetic_model, key="cb_sibernetic"
    )


spacing = 50

NEUROML_FILE = "NeuroML2/c302_D_Full.net.nml"


# The loaded NeuroML document is read once and then kept by Streamlit, so
# changing the cell selection only re-adds cells to a new plotter. The document
# is not modified when adding it to a plotter, so sharing it is safe.
get_neuroml_doc = (
    st.cache_resource(show_spinner=False)(load_neuroml_model)
    if st_mode
    else load_neuroml_model
)


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


def build_scene(sibernetic, neuroml, vw_muscles, vw_neurons, only_show=()):
    """Build a plotter containing the selected models"""
    # Off-screen in Streamlit mode: the script runs on a non-main thread, where
    # on-screen rendering (e.g. Cocoa on macOS) aborts
    plotter = pv.Plotter(window_size=[800, 800], off_screen=st_mode)
    if st_mode:
        plotter.set_background("#9dbe45")  # match the page (OpenWorm green)

    if vw_neurons:
        print_("Adding VirtualWorm neurons...")
        add_virtualworm_neurons(
            plotter,
            translate=((-0.8 * spacing - (vw_muscles * spacing)), 0, 0),
            only_show=list(only_show),
        )

    if vw_muscles:
        print_("Adding VirtualWorm muscles...")
        add_virtualworm_muscles(
            plotter, translate=(-1 * spacing, 0, 0), only_show=list(only_show)
        )

    if neuroml:
        print_("Adding NeuroML model...")
        add_neuroml_model(
            plotter,
            get_neuroml_doc(NEUROML_FILE),
            somas_only=False,
            factor=0.2,
            rotate_x=-90,
            only_show=list(only_show),
        )  # at 0...

    if sibernetic:
        print_("Adding Sibernetic model...")
        add_sibernetic_model(
            plotter, swap_y_z=True, offset3d=(spacing, -50, -100), show_footprint=False
        )

    plotter.set_viewup([0, 10, 0])
    return plotter


only_show = []
if st_mode:
    groups, all_cell_ids = get_cell_groups(NEUROML_FILE)
    group = st.selectbox(
        "Cells to show (NeuroML and VirtualWorm models):",
        list(groups.keys()),
        key="sel_cell_group",
        label_visibility="collapsed",
        help="Which cells to show, applied to the NeuroML and VirtualWorm models",
    )
    if groups[group] is None:
        only_show = st.multiselect(
            "Choose cells:",
            all_cell_ids,
            default=["AVAL", "AVAR"],
            key="sel_cells",
            label_visibility="collapsed",
        )
    else:
        only_show = groups[group]

selection = (
    adding_sibernetic_model,
    adding_neuroml_model,
    adding_virtualworm_muscles,
    adding_virtualworm_neurons,
    tuple(only_show),
)

if st_mode:
    with st.spinner("Worm models are being loading...", show_time=True):
        plotter = build_scene(*selection)
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
        view_key = "pv_Sib%d_NML%d_VWM%d_VWN%d" % (
            adding_sibernetic_model,
            adding_neuroml_model,
            adding_virtualworm_muscles,
            adding_virtualworm_neurons,
        )
        view_key += "_%d" % hash(tuple(only_show))

        # The panel backend needs no extra dependencies (the default, trame, does)
        stpyvista(plotter, backend="panel", key=view_key)
    pass
else:
    plotter.show()
