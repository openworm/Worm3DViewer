import pyvista as pv
import sys

st_mode = "-gui" not in sys.argv

print("Starting it all...")

if st_mode:
    import streamlit as st

    st.set_page_config(layout="wide")

    from stpyvista.utils import start_xvfb

    if "IS_XVFB_RUNNING" not in st.session_state:
        start_xvfb()
        st.session_state.IS_XVFB_RUNNING = True

    st.title("OpenWorm 3D Viewer")


## Initialize a plotter object
plotter = pv.Plotter(window_size=[800, 600])

print("Read objs...")

plotter.add_axes()
plotter.enable_mesh_picking(show_message=True)

sphere = pv.Sphere(end_theta=90)
plotter.add_mesh(sphere)

## Final touches
plotter.view_isometric()
# plotter.add_scalar_bar()
plotter.background_color = "white"

print("Created the scene...")

if st_mode:
    ## Pass a key to avoid re-rendering at each page change
    if True:
        from stpyvista import stpyvista

        stpyvista(plotter, key="pv_cube")
    pass
else:
    plotter.show()
