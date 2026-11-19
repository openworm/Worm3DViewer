from neuromlmodel import add_neuroml_model  # noqa: F401
from SiberneticReplay import add_sibernetic_model  # noqa: F401
from virtualworm import add_virtualworm_muscles  # noqa: F401
from virtualworm import add_virtualworm_neurons  # noqa: F401

import os
import platform
import shutil
import subprocess
import sys

import pyvista as pv

version = "v0.3.1"

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

    st.title("OpenWorm 3D Viewer (%s)" % version)

    st.markdown(
        "This is a 3D viewer for a number of OpenWorm _C. elegans_ models and datasets. It uses PyVista for rendering..."
    )
    st.markdown(
        "Using pyvista %s, stpyvista %s, and streamlit %s"
        % (pv.__version__, stpyvista_version, st.__version__)
    )

## Default selection of models to show (the checkboxes below override these
## in Streamlit mode)
adding_sibernetic_model = False
adding_neuroml_model = True
adding_virtualworm_muscles = False
adding_virtualworm_neurons = False

if st_mode:
    st.markdown("**Select the WORM models to view:**")
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
    plotter = pv.Plotter(window_size=[800, 600], off_screen=st_mode)

    if sibernetic:
        print_("Adding Sibernetic model...")
        add_sibernetic_model(
            plotter, swap_y_z=True, offset3d=(spacing, -50, -100), show_footprint=False
        )

    if neuroml:
        print_("Adding NeuroML model...")
        add_neuroml_model(
            plotter,
            "NeuroML2/c302_D_Full.net.nml",
            somas_only=False,
            factor=0.2,
            rotate_x=-90,
            only_show=list(only_show),
        )  # at 0...

    if vw_muscles:
        print_("Adding VirtualWorm muscles...")
        add_virtualworm_muscles(
            plotter, translate=(-1 * spacing, 0, 0), only_show=list(only_show)
        )

    if vw_neurons:
        print_("Adding VirtualWorm neurons...")
        add_virtualworm_neurons(
            plotter, translate=(-1.8 * spacing, 0, 0), only_show=list(only_show)
        )

    plotter.set_viewup([0, 10, 0])
    return plotter


only_show = []
if st_mode:
    groups, all_cell_ids = get_cell_groups(NEUROML_FILE)
    group = st.selectbox(
        "Cells to show (applied to the NeuroML and VirtualWorm models):",
        list(groups.keys()),
        key="sel_cell_group",
    )
    if groups[group] is None:
        only_show = st.multiselect(
            "Choose cells:", all_cell_ids, default=["AVAL", "AVAR"], key="sel_cells"
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
