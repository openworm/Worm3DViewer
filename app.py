from neuromlmodel import add_neuroml_model  # noqa: F401
from siberneticmodel import add_sibernetic_model  # noqa: F401

import pyvista as pv
import sys

version = "v0.5"

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


add_sibernetic_model(plotter)

sphere = pv.Sphere(end_theta=60, radius=10, center=(0, 0, 0))
plotter.add_mesh(sphere)
plotter.set_background("white")
plotter.add_axes()

add_neuroml_model(plotter, somas_only=True)

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
