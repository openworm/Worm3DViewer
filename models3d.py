"""The 3D models that the web viewer can show, in one place.

Each model is a Model3D: its key, the label and description of its checkbox,
whether it is shown by default, how to load its data (from the mesh cache, see
meshcache.py) and how to add it to a plotter. The app builds its checkboxes and
the 3D scene from the list in Models3D.models, so to add a model:

  1. write its loader and `add_*` function (taking `only_show` and `colors`; see
     CLAUDE.md), and a -cache option if it should use the mesh cache,
  2. add a function here that places it (a translate, a scale, ...) and calls its
     `add_*` function, and
  3. add a Model3D for it to Models3D.models.

The order of that list is the order of the checkboxes (filling two columns across)
and of the models in the scene.
"""

import functools
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from neuromlmodel import add_neuroml_meshes, load_neuroml_cache, save_neuroml_cache
from SiberneticReplay import add_sibernetic_model
from virtualworm import add_virtualworm, load_virtualworm
from witvliet2021 import add_stl_neurons, load_stl_neurons

# Default distance between the worms (the app's slider can lower it)
DEFAULT_SPACING = 50

# The Witvliet et al. 2021 cells are scaled, rotated (degrees about x, y, z) and
# moved (after that, on top of their place next to the VirtualWorm models), to
# match the other models
STL_SCALE = 0.33
STL_ROTATE = (270, 90, 0)
STL_OFFSET = (0, 8, 52)

NEUROML_FULL = "neuroml_full"
NEUROML_SOMAS = "neuroml_somas"
NEUROML_CANONICAL = "canonical"

# The NeuroML models: model key -> the mesh cache, the NeuroML file and the
# scale/rotation (degrees) that its meshes are built with (see
# neuromlmodel.build_neuroml_meshes()). `python models3d.py -cache` builds the caches.
# The order is the order that they are placed along x: each one that is shown is
# `spacing` after the previous one shown, with no gap left for those that are not
# (the first is at 0).
NEUROML_MODELS = {
    # the cells have their own morphologies, in the file's frame
    NEUROML_FULL: dict(
        cache=NEUROML_FULL,
        file="NeuroML2/c302_D_Full.net.nml",
        mesh_params=dict(somas_only=False, factor=0.2, rotate_x=-90),
    ),
    # the same network, but with each cell just a sphere (its soma) at its position,
    # in the same frame as c302
    NEUROML_SOMAS: dict(
        cache=NEUROML_SOMAS,
        file="NeuroML2/c302_C2_Full.net.nml",
        mesh_params=dict(somas_only=False, factor=0.2, rotate_x=-90),
    ),
    # a sphere per neuron, along x (head at 0) up to ~800: scaled and rotated to
    # match the c302 model's frame, and moved by CANONICAL_TRANSLATE
    NEUROML_CANONICAL: dict(
        cache=NEUROML_CANONICAL,
        file="NeuroML2/NeuroPAL_Canonical.net.nml",
        mesh_params=dict(somas_only=False, factor=0.184, rotate_y=90),
    ),
}
NEUROML_KEYS = list(NEUROML_MODELS)

# The canonical neuron positions are moved by this (in the scale and rotation of the
# mesh cache), so that the neurons are on the c302 model's somas (a fit to the 300
# cells that both have, with a median distance of ~4.5 units), before being moved
# along x to their place
CANONICAL_TRANSLATE = (0, 4, 65)


def _load_neuroml(key):
    """The (cached) meshes of one of the NEUROML_MODELS, for add_neuroml_meshes()"""
    spec = NEUROML_MODELS[key]
    return load_neuroml_cache(spec["cache"], spec["file"], **spec["mesh_params"])


def build_caches():
    """Make the mesh caches of the NeuroML models (those of the other models are made
    by `virtualworm.py -cache` and `witvliet2021.py -cache`)"""
    for spec in NEUROML_MODELS.values():
        save_neuroml_cache(spec["cache"], spec["file"], **spec["mesh_params"])


@dataclass
class SceneOptions:
    """What is passed to every model when it is added to the scene"""

    selected: dict  # model key -> whether it is shown (to place models by others)
    spacing: float = DEFAULT_SPACING
    only_show: list = field(default_factory=list)  # cell names; empty: all
    highlight: list = field(default_factory=list)  # cell names; empty: none
    colors: dict = field(default_factory=dict)  # cell name -> color; empty: default

    def is_shown(self, key):
        return bool(self.selected.get(key))

    def neuroml_x(self, key=None):
        """Where the NeuroML model `key` is along x: `spacing` for each of the
        NeuroML models before it in NEUROML_KEYS that are shown. For no key, where
        the next model after them all is (e.g. Sibernetic)."""
        before = (
            NEUROML_KEYS if key is None else NEUROML_KEYS[: NEUROML_KEYS.index(key)]
        )
        return sum(self.is_shown(k) for k in before) * self.spacing


@dataclass
class Model3D:
    key: str  # short name; the widget key of the checkbox is "cb_" + key
    label: str  # of the checkbox
    description: str  # the help of the checkbox
    add: Callable[[Any, Any, SceneOptions], None]  # (plotter, data, options)
    load: Optional[Callable[[], Any]] = None  # the data for add; None if none
    default: bool = False  # shown at first


# -- the models: where they are placed, and adding them to a plotter ------------


def _add_virtualworm(plotter, data, o):
    add_virtualworm(
        plotter,
        data,
        translate=(-o.spacing, 0, 0),
        only_show=o.only_show,
        highlight=o.highlight,
        colors=o.colors,
    )


def _add_stl_neurons(plotter, data, o):
    # to the left of the VirtualWorm worms
    x = -(0.8 + o.is_shown("virtualworm")) * o.spacing
    add_stl_neurons(
        plotter,
        data,
        scale=STL_SCALE,
        rotate_x=STL_ROTATE[0],
        rotate_y=STL_ROTATE[1],
        rotate_z=STL_ROTATE[2],
        translate=(x + STL_OFFSET[0], STL_OFFSET[1], STL_OFFSET[2]),
        only_show=o.only_show,
        highlight=o.highlight,
        colors=o.colors,
    )


def _neuroml_adder(key, translate=(0, 0, 0)):
    """The add function of the NeuroML model `key` (see NEUROML_KEYS), whose scale
    and rotation are fixed in its cache. It is moved by translate, then to its place
    along x."""

    def add(plotter, data, o):
        items, info = data
        add_neuroml_meshes(
            plotter,
            items,
            info,
            only_show=o.only_show,
            highlight=o.highlight,
            colors=o.colors,
            translate=(translate[0] + o.neuroml_x(key), translate[1], translate[2]),
        )

    return add


def _add_sibernetic_model(plotter, data, o):
    # (highlight is not supported for the particles)
    add_sibernetic_model(
        plotter,
        swap_y_z=True,
        offset3d=(o.neuroml_x(), -50, -100),  # after the NeuroML models
        show_footprint=False,
        only_show=o.only_show,
        colors=o.colors,
    )


class Models3D:
    """The 3D models available (see the module docstring): `models` is the list
    of them in order.

    cache: a decorator for caching the loading of a model's data, which is then
    read once and shared (and so must not be modified when adding it to a
    plotter). Default: functools.cache; the app passes Streamlit's
    st.cache_resource.
    """

    def __init__(self, cache=functools.cache):
        self.models = [
            Model3D(
                key="virtualworm",
                label="VirtualWorm",
                description="The VirtualWorm 3D model: the neurons and the body wall "
                "muscles (which cover the body). Use the cell selection to show "
                "just the neurons or just the muscles",
                load=lambda: load_virtualworm(use_cache=True),
                add=_add_virtualworm,
                default=True,
            ),
            Model3D(
                key=NEUROML_FULL,
                label="NeuroML model (c302)",
                description="The cells of the c302 NeuroML model",
                load=lambda: _load_neuroml(NEUROML_FULL),
                add=_neuroml_adder(NEUROML_FULL),
            ),
            Model3D(
                key=NEUROML_SOMAS,
                label="NeuroML model (somas only)",
                description="The c302 NeuroML model with each cell just a soma, "
                "at the same positions as the cells of the c302 model",
                load=lambda: _load_neuroml(NEUROML_SOMAS),
                add=_neuroml_adder(NEUROML_SOMAS),
            ),
            Model3D(
                key="sibernetic",
                label="Sibernetic model",
                description="The Sibernetic simulation of the worm body. Cells can "
                "be selected and colored for the muscles, but not highlighted",
                add=_add_sibernetic_model,
            ),
            Model3D(
                key="stl",
                label="Witvliet et al. 2021 adult cells",
                description="The cells of the nerve ring region of an adult, from "
                "the electron microscopy of Witvliet et al. (2021)",
                load=lambda: load_stl_neurons(use_cache=True),
                add=_add_stl_neurons,
            ),
            Model3D(
                key=NEUROML_CANONICAL,
                label="Canonical atlas (Skuhersky et al. 2022)",
                description='"Canonical" neuron positions, as calculated in: Toward a more accurate 3D atlas of C. elegans neurons (Skuhersky et al. 2022).',
                load=lambda: _load_neuroml(NEUROML_CANONICAL),
                add=_neuroml_adder(NEUROML_CANONICAL, CANONICAL_TRANSLATE),
            ),
        ]
        self._by_key = {m.key: m for m in self.models}
        # each loader is cached on its own (not a function of self, which can't be
        # hashed by Streamlit's cache)
        self._loaders = {m.key: cache(m.load) for m in self.models if m.load}

    @property
    def keys(self):
        return [m.key for m in self.models]

    def defaults(self):
        """dict of model key -> whether it is shown at first"""
        return {m.key: m.default for m in self.models}

    def from_query(self, values):
        """The models to show at first, given the values of the URL's `model3d`
        query parameter (a list of strings, each of which can hold several model
        keys separated by commas). Returns (dict of model key -> shown, list of
        the unknown keys). With no values, the defaults (as defaults())."""
        requested = [k.strip() for v in values for k in v.split(",") if k.strip()]
        unknown = [k for k in requested if k not in self._by_key]
        if not [k for k in requested if k not in unknown]:
            return self.defaults(), unknown
        return {m.key: m.key in requested for m in self.models}, unknown

    def get_data(self, key):
        """The (cached) data of a model, for its add function; None if it has no
        load function. Raises meshcache.CacheError if a mesh cache is missing."""
        return self._loaders[key]() if key in self._loaders else None

    def add_to_plotter(self, plotter, options):
        """Add the models selected in options (a SceneOptions) to the plotter"""
        for model in self.models:
            if options.is_shown(model.key):
                print("Adding %s..." % model.label)
                model.add(plotter, self.get_data(model.key), options)

    @staticmethod
    def selection_key(selected):
        """A string for the selection of models, e.g. for a widget key"""
        return "_".join("%s%d" % (k, bool(v)) for k, v in selected.items())


if __name__ == "__main__":
    if "-cache" in sys.argv:
        build_caches()
        sys.exit(0)

    for m in Models3D().models:
        print(
            "%-11s %-34s default:%-5s %s" % (m.key, m.label, m.default, m.description)
        )
