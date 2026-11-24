"""Reading the options that can be given in the URL of the web viewer, e.g.

    ?model3d=virtualworm,witvliet2021adult&show=Sensory neurons&highlight=AVAL,AVAR
    &color=random&background=white&spacing=30

so that a URL can return to a scene. These functions turn the query parameters
into the initial values of the widgets; they return a list of messages for
values that were not understood (which are then ignored).

  model3d     model keys (see models3d.py), comma separated or repeated
  show        a group of cells (as in the Show box, e.g. "Only muscles") or cell
              names, e.g. AVAL,AVAR (as "Specific cells...")
  highlight   as show, or "None"
  color       a color overlay (see coloroverlay.py): the start of its name, e.g.
              random, wormatlas, default ("colour" is also accepted)
  background  a background (e.g. white)
  spacing     the spacing of the worms: a number
"""

import re

SPECIFIC = "Specific cells..."


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _split(values):
    """["a,b", "c"] -> ["a", "b", "c"]"""
    return [p.strip() for v in values for p in v.split(",") if p.strip()]


def match_option(value, options, prefix=False):
    """The option that `value` names, ignoring case and punctuation; with prefix, a
    value that is the start of an option's name also matches (the first such
    option). None if none."""
    v = _norm(value)
    if not v:
        return None
    for o in options:
        if _norm(o) == v:
            return o
    if prefix:
        for o in options:
            if _norm(o).startswith(v):
                return o
    return None


def cell_choice(values, group_names, cell_ids):
    """For show/highlight: (group, cells): the group (one of group_names) to select
    and, if that is SPECIFIC, the chosen cells. group is None if there are no
    values; otherwise one understood. Also returns the messages."""
    problems = []
    parts = _split(values)
    if not parts:
        return None, [], problems
    group = match_option(values[-1], group_names) if len(values) == 1 else None
    if group and group != SPECIFIC:
        return group, [], problems
    by_name = {c.lower(): c for c in cell_ids}
    cells = []
    for p in parts:
        if p.lower() in by_name:
            cells.append(by_name[p.lower()])
        else:
            problems.append("unknown cell or group '%s'" % p)
    if not cells:
        return None, [], problems
    return SPECIFIC, cells, problems


def single(values, name, options, prefix=False, problems=None):
    """The option named by the (last) value of a parameter, or None"""
    if not values:
        return None
    found = match_option(values[-1], options, prefix)
    if found is None and problems is not None:
        problems.append(
            "unknown %s '%s' (use one of: %s)" % (name, values[-1], ", ".join(options))
        )
    return found


def number(values, name, low, high, problems=None):
    """The number in the (last) value of a parameter, limited to low..high, or None"""
    if not values:
        return None
    try:
        return min(max(float(values[-1]), low), high)
    except ValueError:
        if problems is not None:
            problems.append("%s '%s' is not a number" % (name, values[-1]))
        return None


class Options:
    """The initial values of the controls, from the options of a URL or a splash
    scene: models (dict model key -> shown), show/highlight (a group name) and
    show_cells/highlight_cells (cell names for "Specific cells..."), colors,
    background and spacing. problems: messages for what was not understood."""

    def __init__(
        self,
        get,
        models3d,
        groups,
        highlight_options,
        cell_ids,
        color_options,
        backgrounds,
        max_spacing,
    ):
        """get(name) -> the list of values of the parameter `name` (can be empty)"""
        self.problems = []
        self.models, unknown = models3d.from_query(get("model3d"))
        if unknown:
            self.problems.append(
                "unknown model3d %s (use: %s)"
                % (", ".join(unknown), ", ".join(models3d.keys))
            )
        self.show, self.show_cells, p = cell_choice(get("show"), groups, cell_ids)
        self.problems += ["show: " + m for m in p]
        self.highlight, self.highlight_cells, p = cell_choice(
            get("highlight"), highlight_options, cell_ids
        )
        self.problems += ["highlight: " + m for m in p]
        self.show = self.show or "Only neurons"
        self.highlight = self.highlight or "None"
        self.colors = (
            single(
                get("color") or get("colors") or get("colour") or get("colours"),
                "color",
                color_options,
                True,
                self.problems,
            )
            or color_options[0]
        )
        self.background = (
            single(
                get("background"), "background", list(backgrounds), False, self.problems
            )
            or "Green"
        )
        spacing = number(get("spacing"), "spacing", 0, max_spacing, self.problems)
        self.spacing = int(max_spacing if spacing is None else spacing)

    def widget_values(self, models3d):
        """dict of widget key -> value, to set the controls to these options"""
        values = {"cb_" + k: v for k, v in self.models.items()}
        values.update(
            sel_cell_group=self.show,
            sel_cells=self.show_cells or DEFAULT_SPECIFIC_CELLS,
            sel_highlight_group=self.highlight,
            sel_hl_cells=self.highlight_cells,
            sel_colors=self.colors,
            sel_background=self.background,
            sel_spacing=self.spacing,
        )
        return values


DEFAULT_SPECIFIC_CELLS = ["AVBL", "AVBR"]
