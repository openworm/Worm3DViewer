import pyvista as pv

import sys
import glob
import random

TEST_FILE = "AVFL-SEM_adult.stl"


def add_test_neuron(plotter, scale=20, translate=(-80, 0, 0)):
    files = glob.glob("catmaid-data-explorer/server/3d-models/*.stl")
    for f in files:
        print("Adding file %s..." % f)

        mesh = pv.read(f)

        mesh.scale(scale, inplace=True)
        mesh.rotate_y(270, inplace=True)
        mesh.translate(translate, inplace=True)

        plotter.add_mesh(
            mesh,
            smooth_shading=True,
            color=(random.random(), random.random(), random.random()),
        )

    """'

    # plotter.add_mesh(mesh2, smooth_shading=True, color="orange")
    conn = mesh2.connectivity("all")
    plotter.add_mesh(
        conn,
        smooth_shading=True,
        cmap="jet",
    )
    #plotter.remove_scalar_bar("RegionId")
    """


if __name__ == "__main__":
    pl = pv.Plotter()

    add_test_neuron(pl, scale=1, translate=(-80, 0, 0))

    pl.set_background("white")
    pl.add_axes()

    if "-nogui" not in sys.argv:
        pl.show()
