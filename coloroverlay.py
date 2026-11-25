"""Color overlays: dicts of cell name -> color, to color the cells of the models.

The loaders (add_neuroml_model(), add_virtualworm_neurons(), add_stl_neurons(),
add_sibernetic_model(), ...) take a `colors` dict of cell name -> color and use
it instead of the color the model has for those cells; cells that are not in it
keep their own color. An empty dict is the default colors.

ColorOverlay makes those dicts for the options offered in the web viewer:

    overlay = ColorOverlay()
    overlay.options                                  # names of the options
    colors = overlay.get_colors("WormAtlas cell colors", ["ADAL", "MDL01"])
"""

import zlib

import numpy as np


class ColorOverlay:
    WORMATLAS = "WormAtlas cell colors"
    WORMATLAS_SIB = "WormAtlas + Sibernetic colors"
    DEFAULT = "Default (3D models' own colors)"
    RANDOM = "Random color per cell"

    # The options, with a description of each. The first is the default one
    DESCRIPTIONS = {
        WORMATLAS: 'The standard <a href="https://www.wormatlas.org/colorcode.htm">WormAtlas colors for each cell type</a>',
        WORMATLAS_SIB: 'The standard <a href="https://www.wormatlas.org/colorcode.htm">WormAtlas colors for each cell type</a>, with muscle colors according to Sibernetic (Palyanov et al. 2018, Fig 2)',
        DEFAULT: "Uses the native colors given to each cell by each individual model.",
        RANDOM: "A random color is assigned to each named cell, and used consistently across all model visualizations",
    }

    @property
    def options(self):
        """The names of the options, the default one first"""
        return list(self.DESCRIPTIONS)

    def get_colors(self, option, names, seed=0):
        """A dict of cell name -> color for the given option, for the cells
        `names`. Empty (the models use their own colors) for the default option.

        seed: for the random option, which set of random colors (0 is the first;
        another gives a new set, which is again the same for every call with it).

        Raises ValueError for an unknown option."""
        if option == self.DEFAULT:
            return {}
        if option == self.RANDOM:
            return self._random_colors(names, seed)
        if option == self.WORMATLAS:
            return self._wormatlas_colors(names)
        if option == self.WORMATLAS_SIB:
            wa_sib_colors = self._wormatlas_colors(names)
            for name in names:
                if (
                    name.startswith("MD")
                    or name.startswith("MVL")
                    or name.startswith("MVR")
                ):
                    index = int(name[3:])
                    wa_sib_colors[name] = (
                        "#faa2a2"
                        if index % 4 == 1
                        else "#e0b0f6"
                        if index % 4 == 2
                        else "#fcd268"
                        if index % 4 == 3
                        else "#79ffff"
                    )

            return wa_sib_colors

        raise ValueError(
            "Unknown color option %r: use one of %s" % (option, self.options)
        )

    # A random color is redrawn if it is closer than this to white (the distance in
    # rgb, which is at most sqrt(3)), as it would not show on a white background
    MIN_DISTANCE_FROM_WHITE = 0.5

    @classmethod
    def _random_color(cls, name, seed=0):
        """A random rgb color for a name (and seed) that is always the same for them,
        and not too close to white"""
        key = zlib.crc32(name.encode())
        rng = np.random.default_rng(key if seed == 0 else [key, seed])
        while True:
            color = rng.random(3)
            if np.linalg.norm(1.0 - color) >= cls.MIN_DISTANCE_FROM_WHITE:
                return tuple(float(v) for v in color)

    @classmethod
    def _random_colors(cls, names, seed=0):
        """A random (but repeatable for a given name and seed) rgb color per name,
        none of them too close to white"""
        return {name: cls._random_color(name, seed) for name in names}

    @staticmethod
    def _wormatlas_colors(names):
        """The standard WormAtlas color (a hex string, e.g. "#336600") of each
        cell, from cect.Cells.get_standard_color(). The cells that it doesn't know
        are left out."""
        from cect.Cells import get_standard_color

        colors = {}
        for name in names:
            try:
                colors[name] = get_standard_color(name)
            except Exception:  # "Unknown cell": no WormAtlas color for it
                pass
        return colors


if __name__ == "__main__":
    overlay = ColorOverlay()
    names = ["ADAL", "AVAL", "DB1", "I1L", "MDL01", "hmc", "not_a_cell"]
    for option in overlay.options:
        print("%s: %s" % (option, overlay.get_colors(option, names)))
