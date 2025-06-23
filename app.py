from neuromlmodel import add_neuroml_model  # noqa: F401
from siberneticmodel import add_sibernetic_model  # noqa: F401
from virtualworm import add_virtualworm_muscles  # noqa: F401
from virtualworm import add_virtualworm_neurons  # noqa: F401

import pyvista as pv
import sys

version = "v0.0.8"

st_mode = "-gui" not in sys.argv

print("Starting OpenWorm 3D Viewer (%s)" % version)

if st_mode:
    import streamlit as st

    st.set_page_config(layout="wide")

    from stpyvista.utils import start_xvfb

    if "IS_XVFB_RUNNING" not in st.session_state:
        print("Starting XVFB...")
        start_xvfb()
        st.session_state.IS_XVFB_RUNNING = True

    st.title("OpenWorm 3D Viewer (%s)" % version)

    st.markdown(
        "This is a 3D viewer for a number of OpenWorm _C. elegans_ models and datasets. It uses PyVista for rendering..."
    )


## Initialize a plotter object
plotter = pv.Plotter(window_size=[800, 600])

print("Read objs...")

plotter = pv.Plotter()


spacing = 50

add_sibernetic_model(plotter, swap_y_z=True, offset=spacing)
add_neuroml_model(plotter, "NeuroML2/c302_A_Full.net.nml", somas_only=False)  # at 0...
add_virtualworm_muscles(plotter, translate=(-1 * spacing, 0, 0))
# add_virtualworm_neurons(plotter, translate=(-1.8*spacing, 0, 0))


plotter.set_viewup([0, 10, 0])


print("Created the scene...")

if st_mode:
    ##
    if True:
        print("Pass a key to avoid re-rendering at each page change")
        from stpyvista import stpyvista

        stpyvista(plotter, key="pv_cube")
    pass
else:
    plotter.show()
