import pyvista as pv

import sys

BODY_WALL_MUSCLE_OBJ_FILE = "bwm.obj"
NEURONS_OBJ_FILE = "neurons.obj"


def add_virtualworm_muscles(plotter, scale=20, translate=(-40, 0, 0)):
    print("Adding virtual worm file %s..." % BODY_WALL_MUSCLE_OBJ_FILE)
    mesh = pv.read(BODY_WALL_MUSCLE_OBJ_FILE)

    mesh.scale(scale, inplace=True)
    mesh.translate((translate), inplace=True)

    conn = mesh.connectivity("all")

    plotter.add_mesh(conn, smooth_shading=True, color="green")


def add_virtualworm_neurons(plotter, scale=20, translate=(-80, 0, 0)):
    print("Adding virtual worm file %s..." % NEURONS_OBJ_FILE)
    mesh2 = pv.read(NEURONS_OBJ_FILE)
    mesh2.scale(scale, inplace=True)
    mesh2.translate(translate, inplace=True)

    # plotter.add_mesh(mesh2, smooth_shading=True, color="orange")
    conn = mesh2.connectivity("all")
    plotter.add_mesh(
        conn,
        smooth_shading=True,
        cmap="jet",
    )


if __name__ == "__main__":
    pl = pv.Plotter()

    add_virtualworm_muscles(pl)
    add_virtualworm_neurons(pl)

    pl.set_background("white")
    pl.add_axes()

    if "-nogui" not in sys.argv:
        pl.show()
