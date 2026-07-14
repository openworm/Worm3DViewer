import pyvista as pv
import sys

from neuromlmodel import add_neuroml_model  # noqa: F401
from SiberneticReplay import add_sibernetic_model  # noqa: F401
from virtualworm import add_virtualworm_muscles  # noqa: F401
from virtualworm import add_virtualworm_neurons  # noqa: F401
from virtualworm import print_picked_name  # noqa: F401



if __name__ == "__main__":
    plotter = pv.Plotter()

    spacing = 50

    add_sibernetic_model(
        plotter, swap_y_z=True, offset3d=(spacing, -50, -100), show_footprint=False
    )
    add_neuroml_model(
        plotter,
        "NeuroML2/c302_D_Full.net.nml",
        somas_only=False,
        factor=0.2,
        rotate_x=-90,
    )  # at 0...
    add_virtualworm_muscles(plotter, translate=(-1 * spacing, 0, 0))
    add_virtualworm_neurons(plotter, translate=(-1.8 * spacing, 0, 0))

    plotter.set_background("white")
    plotter.set_viewup([0, 10, 0])

    '''
    # Slow it significantly...
    plotter.enable_mesh_picking(
        callback=print_picked_name,
        use_actor=True,
        left_clicking=True,
        show_message=False,
    )'''

    # plotter.add_axes()

    if "-nogui" not in sys.argv:
        plotter.show()
