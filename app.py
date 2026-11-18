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

version = "v0.2.0"

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


## Initialize a plotter object
# Off-screen in Streamlit mode: the script runs on a non-main thread, where
# on-screen rendering (e.g. Cocoa on macOS) aborts
plotter = pv.Plotter(window_size=[800, 600], off_screen=st_mode)

adding_sibernetic_model = False
adding_neuroml_model = False
adding_virtualworm_muscles = True
adding_virtualworm_neurons = False

spacing = 50


if adding_sibernetic_model:
    print_("Adding Sibernetic model...")
    add_sibernetic_model(
        plotter, swap_y_z=True, offset3d=(spacing, -50, -100), show_footprint=True
    )

if adding_neuroml_model:
    print_("Adding NeuroML model...")
    add_neuroml_model(
        plotter,
        "NeuroML2/c302_D_Full.net.nml",
        somas_only=False,
        factor=0.2,
        rotate_x=-90,
    )  # at 0...

if adding_virtualworm_muscles:
    print_("Adding VirtualWorm muscles...")
    add_virtualworm_muscles(plotter, translate=(-1 * spacing, 0, 0))

if adding_virtualworm_neurons:
    print_("Adding VirtualWorm neurons...")
    add_virtualworm_neurons(plotter, translate=(-1.8 * spacing, 0, 0))

plotter.set_viewup([0, 10, 0])


print_("Created the scene...")

if st_mode:
    ##
    if True:
        print_("Pass a key to avoid re-rendering at each page change")
        from stpyvista import stpyvista

        # The panel backend needs no extra dependencies (the default, trame, does)
        stpyvista(plotter, backend="panel", key="pv_cube")
    pass
else:
    plotter.show()
