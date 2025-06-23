import pyvista as pv
import sys

last_mesh = None

all_points = []
all_point_types = []

colours = {1.1: "lightblue", 2.1: "green", 2.2: "turquoise", 3: "#eeeeee"}
colours = {1.1: "blue", 2.2: "turquoise"}

plotter = None

offset_ = 50


def add_sibernetic_model(pl, swap_y_z=False, offset=50):
    global all_points, all_point_types, last_mesh, plotter, offset_
    offset_ = offset
    plotter = pl

    points = []
    types = []

    file = "pressure_buffer.txt"
    file = "position_buffer.txt"

    line_count = 0
    pcount = 0
    time_count = 0
    logStep = None

    include_boundary = False

    for line in open(file):
        ws = line.split()
        # print(ws)
        if line_count == 6:
            numOfElasticP = int(ws[0])
        if line_count == 7:
            numOfLiquidP = int(ws[0])
        if line_count == 8:
            numOfBoundaryP = int(ws[0])
        if line_count == 9:
            timeStep = float(ws[0])  # noqa: F841
        if line_count == 10:
            logStep = int(ws[0])

        if len(ws) == 4:
            type = float(ws[3])

            if not (type == 3 and not include_boundary):
                if swap_y_z:
                    points.append([float(ws[1]), 1 * float(ws[0]), float(ws[2])])
                else:
                    points.append([float(ws[0]), float(ws[1]), float(ws[2])])
                types.append(type)

        if logStep is not None:
            pcount += 1

            if pcount == numOfBoundaryP + numOfElasticP + numOfLiquidP:
                print(
                    "End of one batch of %i added, %i total points at line %i, time: %i"
                    % (len(points), pcount, line_count, time_count)
                )
                all_points.append(points)
                all_point_types.append(types)

                points = []
                types = []
                pcount = 0
                numOfBoundaryP = 0

                time_count += 1

        line_count += 1

    # all_points_np = np.array(all_points)

    print(
        "Loaded positions with %i elastic, %i liquid and %i boundary points (%i total), %i lines"
        % (
            numOfElasticP,
            numOfLiquidP,
            numOfBoundaryP,
            numOfElasticP + numOfLiquidP + numOfBoundaryP,
            line_count,
        )
    )

    print("Num of time points found: %i" % len(all_points))

    create_mesh(0)

    plotter.remove_scalar_bar("types")

    max_time = len(all_points) - 1
    pl.add_slider_widget(create_mesh, rng=[0, max_time], value=30, title="Time point")
    pl.add_timer_event(max_steps=5, duration=2, callback=create_mesh)


def create_mesh(step):
    import time

    step_count = step
    value = step_count
    global all_points, all_point_types, last_mesh, plotter, offset_

    index = int(value)

    print("Changing to time point: %s (%s) " % (index, value))
    curr_points = all_points[index]
    curr_types = all_point_types[index]

    if last_mesh is None:
        last_mesh = pv.PolyData(curr_points)
        last_mesh["types"] = curr_types
        last_mesh.translate((0, -1000, 0), inplace=True)
        print(last_mesh)

        # last_actor =
        plotter.add_mesh(
            last_mesh,
            render_points_as_spheres=True,
            cmap=[c for c in colours.values()],
            point_size=3,
        )
    else:
        last_mesh.points = curr_points
        last_mesh.translate((offset_, -50, -100), inplace=True)

    plotter.render()

    time.sleep(0.1)

    return


if __name__ == "__main__":
    plotter = pv.Plotter()

    add_sibernetic_model(plotter, swap_y_z=True)
    plotter.set_background("lightgrey")
    plotter.add_axes()
    # plotter.set_viewup([0, 0, 10])

    if "-nogui" not in sys.argv:
        plotter.show()
