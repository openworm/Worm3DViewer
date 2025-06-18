import pyvista as pv

import sys

from pyneuroml import pynml
from pyneuroml.utils import extract_position_info
from neuroml import Cell


def add_neuroml_model(pl):
    filename = "c302_D_Full.net.nml"

    nml_doc = pynml.read_neuroml2_file(filename, include_includes=True)

    print("Loaded NeuroML file: %s" % filename)

    (
        cell_id_vs_cell,
        pop_id_vs_cell,
        positions,
        pop_id_vs_color,
        pop_id_vs_radii,
    ) = extract_position_info(nml_doc, False)

    factor = 0.2

    while pop_id_vs_cell:
        pop_id, cell = pop_id_vs_cell.popitem()
        pos_pop = positions[pop_id]  # type: typing.Dict[typing.Any, typing.List[float]]

        print("Pop: %s has %i of component %s" % (pop_id, len(pos_pop), cell.id))

        radius = pop_id_vs_radii[pop_id] if pop_id in pop_id_vs_radii else 10
        color = pop_id_vs_color[pop_id] if pop_id in pop_id_vs_color else "r"

        if type(cell) is Cell:
            print("Loading a cell with %i segments" % len(cell.morphology.segments))

            cell_meshes = pv.MultiBlock()

            for seg in cell.morphology.segments:
                p = cell.get_actual_proximal(seg.id)
                d = seg.distal
                width = (p.diameter + d.diameter) / 4
                # print("Creating %s" % (seg))

                if cell.get_segment_length(seg.id) == 0:
                    seg_mesh = pv.Sphere(
                        center=(p.x * factor, p.z * factor, -1 * p.y * factor),
                        radius=p.diameter * factor / 2,
                    )

                    pl.add_mesh(seg_mesh, color=color)
                else:
                    seg_mesh = pv.Tube(
                        pointa=(p.x * factor, p.z * factor, -1 * p.y * factor),
                        pointb=(d.x * factor, d.z * factor, -1 * d.y * factor),
                        resolution=1,
                        radius=width * factor,
                        n_sides=15,
                    )

                cell_meshes.append(seg_mesh)

            while pos_pop:
                cell_index, pos = pos_pop.popitem()
                pp = [pos[0] * factor, pos[2] * factor, -1 * pos[1] * factor]
                print("Plotting %s(%i) at %s, %s" % (cell.id, cell_index, pos, pp))
                cell_mesh = cell_meshes.copy()
                for i in range(len(cell_mesh)):
                    cell_mesh[i].translate(pp, inplace=True)
                pl.add_mesh(cell_mesh, color=color, smooth_shading=True)

        else:
            sphere = pv.Sphere(center=(pos[0], pos[1], pos[2]), radius=radius)

            pl.add_mesh(sphere, color=color)


if __name__ == "__main__":
    pl = pv.Plotter()

    add_neuroml_model(pl)
    pl.set_background("white")
    pl.add_axes()

    if "-nogui" not in sys.argv:
        pl.show()
