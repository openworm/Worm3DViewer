import pyvista as pv

import sys


from neuromlmodel import add_neuroml_model

if __name__ == "__main__":
    plotter = pv.Plotter()

    add_neuroml_model(
        plotter, "NeuroML2/NeuroPAL_All_straightened.net.nml", somas_only=True
    )
    plotter.set_background("white")
    plotter.add_axes()

    if "-nogui" not in sys.argv:
        plotter.show()
