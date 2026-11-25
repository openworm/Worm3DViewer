"""The fast 3D view of the Streamlit app (for now opt-in: add ?view=fast to the URL).

Instead of building the scene in a pyvista plotter and sending all of it (100+ MB
for all the models) on every Refresh, as stpyvista does, each model's meshes are
exported once, compressed, and kept by the browser. On a Refresh, only which cells
are shown, faded or hidden, their colors and where each model is placed are sent.
The browser side (fastview_web/) draws them with WebGL2.

Export the models after the mesh caches are built (as in the Dockerfile):

    python fastview.py -export

which writes fastview_web/data/: for each model <key>.<hash>.bin.gz (its meshes as
its add function makes them, with spacing 0 so not moved along x, merged into one
mesh), <key>.<hash>.cells.json (its cells: name, point and triangle ranges, default
color) and index.json.

The meshes are encoded as in Google's webgl-loader (Apache 2.0), which the OpenWorm
Browser uses: vertices in order of first use, positions on a 16-bit grid over the
model's box (14-bit for Witvliet et al. 2021, which is small), stored as zigzagged
differences from the previous vertex, and triangle corners as how far back they are
from the newest vertex (0: the next new one), all as variable-length bytes, then
gzipped. All six models: about 12 MB, against about 125 MB from stpyvista.
"""

import functools
import gzip
import hashlib
import json
import os
import re
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "fastview_web")
DATA_DIR = os.path.join(WEB_DIR, "data")
BITS = {"witvliet2021adult": 14}  # bits of the position grid; 16 for the others
HIDDEN, SHOWN, FADED = 0, 1, 2  # the state of a cell in the view
POINTS_ONLY, HIDDEN_AT_START = 1, 2  # flags of a cell in the cell list


# -- export (once, after the mesh caches are built) --------------------------------


def _varints(values):
    """The values (non-negative ints) as LEB128 bytes"""
    v = np.asarray(values, np.uint64)
    nbytes = np.ones(len(v), np.int64)
    for k in range(1, 10):
        nbytes += v >= (np.uint64(1) << np.uint64(7 * k))
    starts = np.concatenate([[0], np.cumsum(nbytes)[:-1]]).astype(np.int64)
    out = np.zeros(int(nbytes.sum()), np.uint8)
    for k in range(int(nbytes.max()) if len(v) else 0):
        m = nbytes > k
        byte = (v[m] >> np.uint64(7 * k)) & np.uint64(0x7F)
        more = (nbytes[m] > k + 1).astype(np.uint64) << np.uint64(7)
        out[starts[m] + k] = (byte | more).astype(np.uint8)
    return out.tobytes()


def _zigzag(d):
    d = d.astype(np.int64)
    return ((d << 1) ^ (d >> 63)).astype(np.uint64)


def encode(points, triangles, cells, bits=16):
    """The bytes of one model's merged mesh (see the module docstring). Vertices are
    reordered within each cell, so each cell keeps its range of points."""
    order = []
    for c in cells:
        v0, nv, t0, nt = c[1:5]
        own = np.arange(v0, v0 + nv)
        if nt:
            flat = triangles[t0 : t0 + nt].ravel()
            _, first = np.unique(flat, return_index=True)
            used = flat[np.sort(first)]
            own = np.concatenate([used, np.setdiff1d(own, used)])
        order.append(own)
    order = np.concatenate(order).astype(np.int64)
    new_index = np.empty(len(points), np.int64)
    new_index[order] = np.arange(len(points))
    p = points[order].astype(np.float64)
    lo = p.min(0) if len(p) else np.zeros(3)
    size = max(float((p.max(0) - lo).max()), 1e-9) if len(p) else 1.0
    grid = np.round((p - lo) / size * ((1 << bits) - 1)).astype(np.int64)
    body = b"".join(_varints(_zigzag(np.diff(grid[:, j], prepend=0))) for j in range(3))
    corners = new_index[triangles.ravel()]
    if len(corners):
        highest = np.concatenate([[0], np.maximum.accumulate(corners)[:-1] + 1])
        body += _varints(highest - corners)
    head = b"W3D1" + struct.pack(
        "<IIB3x4f", len(points), len(triangles), bits, *lo.astype(np.float32), size
    )
    return head + body


def export_model(models3d, model):
    """The meshes of the model as its add function makes them (all cells, their
    default colors, spacing 0), merged: (points, triangles, cells), where each cell
    is [name, first point, points, first triangle, triangles, color, flags, point
    size]. name is None for objects that are not cells (Sibernetic's particles)."""
    import pyvista as pv

    from models3d import SceneOptions

    plotter = pv.Plotter(off_screen=True)
    models3d.add_to_plotter(
        plotter, SceneOptions(selected={model.key: True}, spacing=0)
    )
    data = models3d.get_data(model.key)
    # the NeuroML models' actors have no names, but are added in the data's order
    names = [n for n, _ in data[0]] if isinstance(data, tuple) else None
    points, triangles, cells = [], [], []
    n_points = n_triangles = 0
    actors = [
        (name, a)
        for name, a in plotter.actors.items()
        if getattr(a, "mapper", None) is not None
        and a.mapper.dataset is not None
        and a.mapper.dataset.n_points
    ]
    if names is not None:
        assert len(names) == len(actors), (model.key, len(names), len(actors))
    for i, (actor_name, actor) in enumerate(actors):
        mesh = actor.mapper.dataset
        if not isinstance(mesh, pv.PolyData):
            mesh = mesh.extract_surface()
        tri = np.zeros((0, 3), np.int64)
        if mesh.n_faces_strict:
            mesh = mesh if mesh.is_all_triangles else mesh.triangulate()
            tri = mesh.faces.reshape(-1, 4)[:, 1:].astype(np.int64)
        if names is not None:
            name = names[i]
        else:
            name = None if actor_name.startswith("PolyData(") else actor_name
        flags = (0 if len(tri) else POINTS_ONLY) | (
            0 if actor.visibility else HIDDEN_AT_START
        )
        color = pv.Color(actor.prop.color).hex_rgb
        cells.append(
            [name, n_points, mesh.n_points, n_triangles, len(tri), color, flags]
            + [float(actor.prop.point_size)]
        )
        points.append(np.asarray(mesh.points, np.float32))
        triangles.append(tri + n_points)
        n_points += mesh.n_points
        n_triangles += len(tri)
    plotter.close()
    return np.concatenate(points), np.concatenate(triangles), cells


def export_all(models3d):
    """Export every model to DATA_DIR (see the module docstring)"""
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    os.makedirs(DATA_DIR)
    index = {}
    for model in models3d.models:
        points, triangles, cells = export_model(models3d, model)
        packed = gzip.compress(
            encode(points, triangles, cells, BITS.get(model.key, 16)), 9, mtime=0
        )
        cell_json = json.dumps(cells, separators=(",", ":")).encode()
        tag = hashlib.sha256(packed + cell_json).hexdigest()[:10]
        files = dict(
            file=f"{model.key}.{tag}.bin.gz", cells=f"{model.key}.{tag}.cells.json"
        )
        with open(os.path.join(DATA_DIR, files["file"]), "wb") as f:
            f.write(packed)
        with open(os.path.join(DATA_DIR, files["cells"]), "wb") as f:
            f.write(cell_json)
        index[model.key] = files
        print(
            "Exported %s: %d cells, %d points, %d triangles, %.2f MB"
            % (model.key, len(cells), len(points), len(triangles), len(packed) / 1e6)
        )
    with open(os.path.join(DATA_DIR, "index.json"), "w") as f:
        json.dump(index, f, indent=1)


# -- the view (on every run of the app) --------------------------------------------


@functools.cache
def _index():
    with open(os.path.join(DATA_DIR, "index.json")) as f:
        return json.load(f)


@functools.cache
def _cells(filename):
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)


@functools.lru_cache(maxsize=4096)
def _hex(color):
    import pyvista as pv

    return pv.Color(color).hex_rgb[1:]


def cell_states(cells, only_show=(), highlight=(), colors={}):
    """For the cells of a model (its exported list): their colors (6 hex digits
    each) and states (HIDDEN, SHOWN or FADED, a digit each), by the same rules as
    the add functions: a cell is shown if only_show is empty or has its name, or its
    name without a part number (MVL22 for MVL22_81); faded if highlight is not empty
    and doesn't have it; colored by colors if there, else its default color.
    Objects that are not cells (no name) are always shown in their own color."""
    only_show, highlight = set(only_show), set(highlight)
    hexes, states = [], []
    for cell in cells:
        name, default, flags = cell[0], cell[5], cell[6]
        base = re.sub(r"_\d+$", "", name) if name else None
        state = SHOWN
        if flags & HIDDEN_AT_START:
            state = HIDDEN
        elif name and only_show and not {name, base} & only_show:
            state = HIDDEN
        elif name and highlight and not {name, base} & highlight:
            state = FADED
        color = colors.get(name, colors.get(base)) if name else None
        if isinstance(color, (list, np.ndarray)):
            color = tuple(float(x) for x in color)
        hexes.append(default[1:] if color is None else _hex(color))
        states.append(str(state))
    return "".join(hexes), "".join(states)


_component = None


def show(models3d, options, background, height=800, key="fastview"):
    """Show the models selected in options (a SceneOptions) in the fast view.
    Raises FileNotFoundError if the models were not exported."""
    global _component
    import streamlit.components.v1 as components

    if _component is None:
        _component = components.declare_component("fastview", path=WEB_DIR)
    index = _index()
    models = []
    for model in models3d.models:
        files = index[model.key]
        item = dict(key=model.key, file=files["file"], cells=files["cells"])
        if options.is_shown(model.key):
            item["x"] = float(model.x(options))
            item["colors"], item["states"] = cell_states(
                _cells(files["cells"]),
                options.only_show,
                options.highlight,
                options.colors,
            )
        models.append(item)
    # the camera is fitted to the models again when they or their places change
    fit = models3d.selection_key(options.selected) + "_%g" % options.spacing
    _component(
        models=models,
        background="#" + _hex(background or "white"),
        fit=fit,
        height=height,
        key=key,
        default=None,
    )


if __name__ == "__main__":
    if "-export" in sys.argv:
        from models3d import Models3D

        export_all(Models3D())
    else:
        print(__doc__)
