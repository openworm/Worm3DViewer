import pyvista as pv
import sys

from neuromlmodel import add_neuroml_model  # noqa: F401
from siberneticmodel import add_sibernetic_model  # noqa: F401
from virtualworm import add_virtualworm_muscles  # noqa: F401
from virtualworm import add_virtualworm_neurons  # noqa: F401

if __name__ == "__main__":
    plotter = pv.Plotter()

    add_virtualworm_muscles(plotter, translate=(-40, 0, 0))
    add_virtualworm_neurons(plotter)

    add_neuroml_model(plotter, "NeuroML2/c302_D_Full.net.nml", somas_only=False)
    add_sibernetic_model(plotter, swap_y_z=True)

    plotter.set_background("white")
    plotter.set_viewup([0, 10, 0])

    plotter.add_axes()

    if "-nogui" not in sys.argv:
        plotter.show()
