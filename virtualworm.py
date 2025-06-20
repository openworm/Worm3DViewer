import pyvista as pv

import sys

BODY_WALL_MUSCLE_OBJ_FILE = "bwm.obj"
NEURONS_OBJ_FILE = "neurons.obj"


def add_virtualworm_muscles(plotter):
    print("Adding virtual worm file %s..." % BODY_WALL_MUSCLE_OBJ_FILE)
    mesh = pv.read(BODY_WALL_MUSCLE_OBJ_FILE)
    mesh.scale(20, inplace=True)
    mesh.translate((-40, 0, 0), inplace=True)

    plotter.add_mesh(mesh, smooth_shading=True, color="green")


def add_virtualworm_neurons(plotter):
    print("Adding virtual worm file %s..." % NEURONS_OBJ_FILE)
    mesh2 = pv.read(NEURONS_OBJ_FILE)
    mesh2.scale(20, inplace=True)
    mesh2.translate((-80, 0, 0), inplace=True)

    plotter.add_mesh(mesh2, smooth_shading=True, color="orange")

    """
    conn = mesh.connectivity('all')
    print(conn)
    # Format scalar bar text for integer values.
    scalar_bar_args = dict(
        fmt='%.f',
    )

    cpos = [(10.5, 12.2, 18.3), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]

    
    conn.plot(
        categories=True,
        cmap='jet',
        scalar_bar_args=scalar_bar_args,
        cpos=cpos,
    )"""


if __name__ == "__main__":
    pl = pv.Plotter()

    add_virtualworm_muscles(pl)

    pl.set_background("white")
    pl.add_axes()

    if "-nogui" not in sys.argv:
        pl.show()
