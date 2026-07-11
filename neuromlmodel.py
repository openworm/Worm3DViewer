import numpy as np
import pyvista as pv

import sys

from pyneuroml import pynml
from pyneuroml.utils import extract_position_info
from neuroml import Cell


def add_neuroml_model(plotter, filename, somas_only=False, factor=0.2):

    nml_doc = pynml.read_neuroml2_file(filename, include_includes=True)

    print("Loaded NeuroML file: %s" % filename)

    (
        cell_id_vs_cell,
        pop_id_vs_cell,
        positions,
        pop_id_vs_color,
        pop_id_vs_radii,
    ) = extract_position_info(nml_doc, False)

    for pop_id, cell in pop_id_vs_cell.items():
        pos_pop = positions[pop_id]  # type: typing.Dict[typing.Any, typing.List[float]]

        print("Pop: %s has %i of component %s" % (pop_id, len(pos_pop), cell.id))

        radius = pop_id_vs_radii[pop_id] if pop_id in pop_id_vs_radii else 0.5
        color = pop_id_vs_color[pop_id] if pop_id in pop_id_vs_color else "r"

        # instance positions of this population, remapped/scaled to viewer axes
        points = np.array(
            [
                [pos[0] * factor, pos[2] * factor, -1 * pos[1] * factor]
                for pos in pos_pop.values()
            ]
        )
        point_cloud = pv.PolyData(points)

        if isinstance(cell, Cell):
            print("Loading a cell with %i segments" % len(cell.morphology.segments))

            seg_meshes = []

            for seg in cell.morphology.segments:
                p = cell.get_actual_proximal(seg.id)
                d = seg.distal
                width = (p.diameter + d.diameter) / 4
                if somas_only and seg.id != 0:
                    continue

                if cell.get_segment_length(seg.id) == 0:
                    seg_mesh = pv.Sphere(
                        center=(p.x * factor, p.z * factor, -1 * p.y * factor),
                        radius=p.diameter * factor / 2,
                    )
                else:
                    seg_mesh = pv.Tube(
                        pointa=(p.x * factor, p.z * factor, -1 * p.y * factor),
                        pointb=(d.x * factor, d.z * factor, -1 * d.y * factor),
                        resolution=1,
                        radius=width * factor,
                        n_sides=15,
                    )

                seg_meshes.append(seg_mesh)

            # one template mesh per cell type, stamped at every instance position
            # via a glyph filter instead of copying/translating it per instance
            cell_mesh = (
                seg_meshes[0].merge(seg_meshes[1:])
                if len(seg_meshes) > 1
                else seg_meshes[0]
            )
            glyphs = point_cloud.glyph(geom=cell_mesh, scale=False, orient=False)
            plotter.add_mesh(glyphs, color=color, smooth_shading=True)

        else:
            sphere = pv.Sphere(radius=radius)
            glyphs = point_cloud.glyph(geom=sphere, scale=False, orient=False)
            plotter.add_mesh(glyphs, color=color)


if __name__ == "__main__":
    plotter = pv.Plotter()

    c302_nml = "NeuroML2/c302_D_Full.net.nml"

    show_gui = True
    if "-nogui" in sys.argv:
        show_gui = False
        sys.argv.remove("-nogui")

    if len(sys.argv) > 1 and sys.argv[1].endswith(".nml"):
        nml_file = sys.argv[1]
    else:
        nml_file = c302_nml

    add_neuroml_model(plotter, nml_file, somas_only=False)
    plotter.set_background("white")
    plotter.add_axes()

    if show_gui:
        plotter.show()
