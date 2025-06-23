import pyvista as pv
import sys

from virtualworm import add_virtualworm_muscles
from virtualworm import add_virtualworm_neurons
from neuromlmodel import add_neuroml_model
from siberneticmodel import add_sibernetic_model

if __name__ == "__main__":
    plotter = pv.Plotter()

    add_virtualworm_muscles(plotter)
    add_virtualworm_neurons(plotter)
    add_neuroml_model(plotter, "NeuroML2/c302_D_Full.net.nml", somas_only=False)
    add_sibernetic_model(plotter)

    plotter.set_background("white")
    plotter.set_viewup([0, 10, 0])

    plotter.add_axes()
    plotter.remove_scalar_bar("RegionId")
    plotter.remove_scalar_bar("types")

    if "-nogui" not in sys.argv:
        plotter.show()
