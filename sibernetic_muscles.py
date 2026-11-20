"""Map the named body wall muscles of a Sibernetic configuration file to the
particles that represent them.

Usage:
    python sibernetic_muscles.py CONFIGURATION_FILE [-o muscles.json]

The result for configuration/worm_alone_half_resolution is in
Sibernetic/muscle_particles_worm_alone_half_resolution.json and is used by
add_sibernetic_model() (SiberneticReplay.py) for its only_show and colors.

Sources: the Sibernetic C++ (the reference; src/sphFluid.cl, src/owHelper.cpp,
src/owWorldSimulation.cpp, src/owPhysicsFluidSimulator.cpp), its README.md, and
Palyanov, Khayrulin & Larson (2018) Phil Trans R Soc B 373(1758),
https://pmc.ncbi.nlm.nih.gov/articles/PMC6158221. The Python in the Sibernetic
repo (e.g. main_sim.py) was deliberately not relied on.


HOW MUSCLES ARE STORED
----------------------
- A muscle is not a set of particles but a set of elastic connections tagged
  with a muscle id. Each elastic particle has 32 connection slots (C++
  MAX_NEIGHBOR_COUNT) in the [connection] section, each being
  (neighbour particle id, rest length, muscle id, unused). Row r of the section
  belongs to elastic particle r // 32. A neighbour id of -1 means an empty slot.
- Connections are stored at both ends (i -> j and j -> i), so there are 2720
  tagged rows but 1360 distinct muscle connections in the half resolution worm.
- The force kernel (sphFluid.cl, pcisph_computeElasticForces) applies
  muscle_activation_signal[k - 1] to a connection when int(muscle id) == k. The
  stored value has a fractional part (.2 to .5, cycling with the row number)
  that the kernel ignores; its meaning is unknown.
- There are MUSCLE_COUNT = 96 muscles (owConfigProperty.cpp): 4 quadrants of 24
  rows. A muscle is a chain of 4 to 35 particles linked by connections that run
  almost exactly along the body (z) axis: an end muscle has 6 connections over 4
  particles, a mid body muscle up to 64 connections over 35 particles. All
  muscle particles are of type 2.2xxx. Adjacent muscles share their end
  particles: 1560 particle entries over 1380 distinct particles.
- A particle index is its 0-based line in the [position] section. Elastic
  particles come first (2290 of them, then 388 liquid, then 31408 boundary), and
  logged frames (position_buffer.txt) list particles in the same order, so the
  indices also address the lines of a logged frame (frames after the first omit
  the boundary particles, which are last). The header of the position buffer
  and the first logged frame match this configuration, which is how the map is
  known to apply to Sibernetic/position_buffer.txt.
- The fractional part of an elastic particle's type encodes the body slice, e.g.
  2.1052 (owPhysicsFluidSimulator.cpp, update_worm_motion_log_file):
  slice = (type - 2.1) * 10000 + 1 for 2.1xxx, and the same from 2.2 for 2.2xxx.
  The slice correlates 0.99999 with z (slices 51 to 149). 2.1xxx (862 particles)
  and 2.2xxx (1428) both exist; 2.25 to 2.35 is a separate agar like type in the
  kernels. What the 2.1 / 2.2 split means is not established.


MUSCLE NAMES
------------
The names come from the order of the activation signals in the C++ display code
(owWorldSimulation.cpp, which prints them in blocks of 24 with the label MDR,
MVR, MVL, MDL and an index offset of 0, 24, 48, 72):

    signal index  0-23  MDR01-24     muscle ids  1-24
    signal index 24-47  MVR01-24                25-48
    signal index 48-71  MVL01-24                49-72
    signal index 72-95  MDL01-24                73-96

so muscle id k (1-based) is signal index k - 1, and MDL01 is id 73. This is the
only explicit naming in the C++. The paper names the quadrants VR, VL, DR, DL and
says the muscle numbering follows WormAtlas, taken from the DL side and then
"copied and mirrored" to the other quadrants.

What the data show (worm_alone_half_resolution; positions relative to the body
centreline, body along z from 11.7 to 171.8):

- Each block of 24 ids is one quadrant: ids 1-24 at +x/-y, 25-48 at -x/-y,
  49-72 at -x/+y, 73-96 at +x/+y. The two blocks the C++ calls dorsal (MD*) share
  +x, so dorsal is +x and ventral -x, which agrees with the paper's start pose
  (ventral left, dorsal right).
- Rows are the same in all four quadrants (same z to within 0.3 units), as
  expected from copying and mirroring.
- Rows 03 to 24 run in strictly decreasing z, from about 158 down to 23. Rows 01
  and 02 are slightly out of order: row 02 is at z 165 to 170 and row 01 at 160
  to 165.


OPEN ISSUES
-----------
1. Which end of the body is the head? Row 01 is at the high z end and row 24 at
   the low z end, and in the VirtualWorm model MDL01 is at the head, which would
   make the high z end the head. But the C++ comment on the worm motion log says
   "from head to tail" while listing slices in increasing z, which would make the
   low z end the head; and the C++ left/right naming only has the right
   handedness if the head is at low z. The body width profile of the two ends was
   too alike to decide. Possible checks: the supplementary material of the paper,
   or driving one muscle in a simulation and seeing which end of the worm moves.
2. Left versus right follows from (1). The pairing of the quadrants (MDR with
   MVR, MDL with MVL) is consistent, but which side is left is not established.
3. Rows 01 and 02 are slightly out of z order (see above): confirm that this is
   intended and not a numbering or naming quirk.
4. The meaning of the fractional part of the muscle id (.2 to .5) and of the
   2.1xxx versus 2.2xxx particle types is unknown.
5. Muscle ids 1-96 are all used, but the paper says 95 body wall muscles in one
   place and 96 in another, keeping one for symmetry. MVL24 (9 particles) is the
   one that is not in the c302 NeuroML network (c302_D_Full has 95 body wall
   muscles), so it cannot be selected or colored by name from the viewer's cell
   lists, though its particles are always drawn.
6. The number of particles per muscle cell, and the order of the signals in the
   supplementary material (Methods 2.5 to 2.7 of the paper, at
   https://dx.doi.org/10.6084/m9.figshare.c.4186424), were not checked against
   the paper; the C++ was treated as the gold standard.
7. Only worm_alone_half_resolution was analysed. Other configurations (full
   resolution, crawling, swimming, immersed, ...) were not checked, and the
   MAX_NEIGHBOR_COUNT of 32 and the elastic first particle order are assumed for
   them. The map is only valid for logs of simulations started from the
   configuration it was made from (add_sibernetic_model checks the first frame
   against the stored positions and warns on a mismatch).
8. Adjacent muscles share end particles, so a particle can belong to two
   muscles. When coloring, the last muscle in the colors dict wins; the
   particles are not split between muscles.
9. Not verified visually in a browser: the coloring and only_show of Sibernetic
   muscles was tested by checking the colors and points of the meshes, and via
   Streamlit's AppTest.
"""

import json
import sys

MAX_NEIGHBOR_COUNT = 32  # connection slots per elastic particle (C++)
NO_PARTICLE_ID = -1
MUSCLE_COUNT = 96
ROWS_PER_QUADRANT = 24
# Order of the quadrants in the muscle activation signals (C++ display code)
QUADRANTS = ["MDR", "MVR", "MVL", "MDL"]


def muscle_name(muscle_id):
    """Name of a muscle from its 1-based id, e.g. 73 -> MDL01"""
    quadrant, row = divmod(muscle_id - 1, ROWS_PER_QUADRANT)
    return "%s%02i" % (QUADRANTS[quadrant], row + 1)


def _read_sections(filename):
    sections = {}
    current = None
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if line.startswith("["):
                current = line
                sections[current] = []
            elif line and current is not None:
                sections[current].append(line.split())
    return sections


def get_muscle_particles(config_file):
    """Read a Sibernetic configuration file and return a dict of muscle name ->
    dict with: id, signal_index, particles (sorted particle indices, i.e.
    0-based lines of the [position] section), connections (list of
    [particle, neighbour] pairs, each connection once) and the position of
    each particle."""
    sections = _read_sections(config_file)
    positions = [[float(v) for v in p] for p in sections["[position]"]]
    connections = sections["[connection]"]

    result = {}
    for row, (jd, _rij0, muscle, _unused) in enumerate(connections):
        neighbour = int(float(jd))
        muscle_id = int(float(muscle))
        if neighbour == NO_PARTICLE_ID or muscle_id <= 0:
            continue
        if muscle_id > MUSCLE_COUNT:
            raise ValueError("Unexpected muscle id %i" % muscle_id)

        particle = row // MAX_NEIGHBOR_COUNT
        name = muscle_name(muscle_id)
        info = result.setdefault(
            name,
            {
                "id": muscle_id,
                "signal_index": muscle_id - 1,
                "particles": set(),
                "connections": set(),
            },
        )
        info["particles"].update((particle, neighbour))
        # connections are stored from both ends: keep each pair once
        info["connections"].add(tuple(sorted((particle, neighbour))))

    for info in result.values():
        info["particles"] = sorted(info["particles"])
        info["connections"] = [list(c) for c in sorted(info["connections"])]
        info["positions"] = {p: positions[p][:3] for p in info["particles"]}
    return dict(sorted(result.items(), key=lambda kv: kv[1]["id"]))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    out_file = None
    if "-o" in sys.argv:
        out_file = sys.argv[sys.argv.index("-o") + 1]

    muscles = get_muscle_particles(sys.argv[1])
    print("Found %i muscles" % len(muscles))
    for name in ("MDL01", "MDL24"):
        if name in muscles:
            print(
                "%s: id %i, particles %s"
                % (name, muscles[name]["id"], muscles[name]["particles"])
            )

    if out_file:
        with open(out_file, "w") as f:
            json.dump(
                {
                    "source": sys.argv[1],
                    "note": "Muscle names follow the Sibernetic C++ signal order "
                    "(MDR, MVR, MVL, MDL; 24 rows each). Particle indices are "
                    "0-based lines of the [position] section. Which end of the "
                    "body row 01 is at (head or tail) is not established.",
                    "muscles": muscles,
                },
                f,
                indent=1,
            )
        print("Wrote %s" % out_file)
