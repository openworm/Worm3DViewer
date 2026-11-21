"""A fast on-disk cache of the named meshes (cells) built by the model loaders.

Building the meshes of a model (parsing OBJ/STL files, decimating, building
NeuroML cells) is slow, but reloading them from here takes a few milliseconds.
Each loader has a -cache option that builds its cache; the Streamlit app only
reads the caches (and shows an error if one is missing).

A cache is one uncompressed NumPy .npz file in the cache folder with, for a list
of (name, mesh) pairs (names are cell names, and can be repeated):

    names       the name of each mesh
    pts         the points of all the meshes, joined: float32, shape (N, 3)
    pt_off      where each mesh's points start in pts (and the end, last)
    tri         the triangles of all the meshes, joined: int32 point indices
                local to their mesh, shape (M, 3)
    tri_off     where each mesh's triangles start in tri (and the end, last)
    normals     (optional) the point normals, same shape as pts
    meta        a JSON string: the params that the meshes were built with and
                an optional info record per mesh (e.g. its default color)

Everything is triangulated when saved. Meshes read back share memory with the
loaded arrays: like the loaded models elsewhere they must not be modified.
"""

import json
import os

import numpy as np
import pyvista as pv

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


class CacheError(RuntimeError):
    """The cache for a model is missing, or was built with different params"""


def cache_path(name):
    return os.path.join(CACHE_DIR, name + ".npz")


def _jsonable(value):
    return json.loads(json.dumps(value, default=lambda o: np.asarray(o).tolist()))


def save_meshes(name, items, params=None, info=None):
    """Save a list of (name, pv.PolyData) as the cache `name`.

    params: dict describing how the meshes were built; load_meshes() only
    accepts the cache if asked for the same params.

    info: optional list, one json-able record (e.g. dict) per mesh.
    """
    points, tris, normals = [], [], []
    for _, mesh in items:
        if not mesh.is_all_triangles:
            mesh = mesh.triangulate()
        points.append(np.asarray(mesh.points, dtype=np.float32))
        tris.append(mesh.faces.reshape(-1, 4)[:, 1:].astype(np.int32))
        normals.append(mesh.point_data.active_normals)

    def offsets(arrays):
        return np.concatenate([[0], np.cumsum([len(a) for a in arrays])]).astype(
            np.int64
        )

    arrays = {
        "names": np.array([n for n, _ in items], dtype=str),
        "pts": np.concatenate(points) if points else np.zeros((0, 3), np.float32),
        "pt_off": offsets(points),
        "tri": np.concatenate(tris) if tris else np.zeros((0, 3), np.int32),
        "tri_off": offsets(tris),
        "meta": np.array(
            json.dumps({"params": _jsonable(params), "info": _jsonable(info)})
        ),
    }
    if items and all(n is not None for n in normals):
        arrays["normals"] = np.concatenate(normals).astype(np.float32)

    os.makedirs(CACHE_DIR, exist_ok=True)
    path = cache_path(name)
    np.savez(path, **arrays)
    print("Saved cache of %i meshes: %s" % (len(items), path))
    return path


def load_meshes(name, params=None):
    """Read the cache `name`. Returns (items, info): the list of (name,
    pv.PolyData) and the list of info records (None where there are none).

    Raises CacheError if there is no such cache, or if params is given and the
    cache was built with other params.
    """
    path = cache_path(name)
    if not os.path.isfile(path):
        raise CacheError(
            "No mesh cache %s: build the caches first by running the loaders "
            "with -cache, e.g. ./test.sh" % path
        )
    with np.load(path, allow_pickle=False) as z:
        names = z["names"]
        pts, pt_off = z["pts"], z["pt_off"]
        tri, tri_off = z["tri"], z["tri_off"]
        normals = z["normals"] if "normals" in z.files else None
        meta = json.loads(str(z["meta"]))

    if params is not None and meta["params"] != _jsonable(params):
        raise CacheError(
            "The mesh cache %s was built with params %s, not %s: rebuild it "
            "with -cache" % (path, meta["params"], _jsonable(params))
        )

    items = []
    for i, mesh_name in enumerate(names):
        t = tri[tri_off[i] : tri_off[i + 1]]
        faces = np.empty((len(t), 4), dtype=np.int64)
        faces[:, 0] = 3
        faces[:, 1:] = t
        mesh = pv.PolyData(pts[pt_off[i] : pt_off[i + 1]], faces.ravel())
        if normals is not None:
            mesh.point_data.active_normals = normals[pt_off[i] : pt_off[i + 1]]
        items.append((str(mesh_name), mesh))

    info = meta["info"] if meta["info"] is not None else [None] * len(items)
    return items, info
