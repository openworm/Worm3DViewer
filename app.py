from coloroverlay import ColorOverlay
from meshcache import CacheError
from models3d import DEFAULT_SPACING, Models3D, SceneOptions

import os
import platform
import shutil
import subprocess
import sys


import pyvista as pv

version = "v0.3.8"

stpyvista_version = "0.1.4"

st_mode = "-gui" not in sys.argv


def print_(msg, print_it=True):  # print_it=False when not verbose
    if print_it:
        pre = "Worm3DViewer >>> "
        print("%s %s" % (pre, msg.replace("\n", "\n" + pre)))


def start_xvfb(display=99, resolution=(1024, 768)):
    """Start a virtual X server for headless rendering.

    Replacement for stpyvista.utils.start_xvfb (removed in stpyvista>=0.2) and
    pyvista.start_xvfb (removed in recent pyvista). Only needed on Linux with no
    display, e.g. in the Docker image.
    """
    if platform.system() != "Linux" or os.environ.get("DISPLAY"):
        return
    if shutil.which("Xvfb") is None:
        print_("Xvfb not found; assuming offscreen rendering is available")
        return
    subprocess.Popen(
        ["Xvfb", f":{display}", "-screen", "0", "%dx%dx24" % resolution],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.environ["DISPLAY"] = f":{display}"


print_("Starting OpenWorm 3D Viewer (%s)" % version)

if st_mode:
    import streamlit as st

    print_("Streamlit mode detected...")

    st.set_page_config(layout="wide")

    if "IS_XVFB_RUNNING" not in st.session_state:
        print_("Starting XVFB...")
        start_xvfb()
        st.session_state.IS_XVFB_RUNNING = True

    # Compact, OpenWorm Browser-like look: green page, small text, tight spacing
    st.markdown(
        """
<style>
:root { --ow-green: #9dbe45; --ow-dark: #4c6a22; --ow-text: #2c4310; }
header[data-testid="stHeader"] { display: none; }
.stApp { background: var(--ow-green); }
.block-container { padding: 0.6rem 1rem 2.6rem 1rem; max-width: 100%; }
div[data-testid="stVerticalBlock"] { gap: 0.35rem; }
div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
.stApp p.ow-title { color: #fff; font-size: 1.25rem; font-weight: 600; margin: 0;
            line-height: 1.5; text-shadow: 0 1px 2px rgba(0,0,0,0.25); }
.ow-title span { font-size: 0.75rem; font-weight: 400; margin-left: 0.6rem;
                 opacity: 0.9; }
.stApp p, .stApp label, .stApp [data-testid="stWidgetLabel"] p {
  font-size: 0.78rem; margin: 0; color: var(--ow-text); }
/* The specific cells pickers are only shown when "Specific cells..." is chosen in
   the selector above them. The controls are in a form (no rerun on a change), so
   this is done in CSS: the selector's input has the chosen option as its value. */
.st-key-sel_cells, .st-key-sel_hl_cells { display: none; }
div[data-testid="stLayoutWrapper"]:has(.st-key-sel_cell_group input[value="Specific cells..."])
  + .st-key-sel_cells,
div[data-testid="stLayoutWrapper"]:has(.st-key-sel_highlight_group input[value="Specific cells..."])
  + .st-key-sel_hl_cells { display: block; }
/* white text on the primary (dark green) buttons, e.g. Refresh */
.stApp button[data-testid^="stBaseButton-primary"] p { color: #fff; }
div[data-testid="stCheckbox"] { min-height: 0; }
div[data-testid="stCheckbox"] label { gap: 0.3rem; }
div[data-testid="stSelectbox"] > div, div[data-testid="stMultiSelect"] > div {
  font-size: 0.78rem; }
div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  min-height: 1.9rem; background: rgba(255,255,255,0.75); border-radius: 1rem; }
/* The panel box: the inner block of the bordered layout wrapper in a column */
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
  > div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"] {
  background: rgba(255,255,255,0.22); border-color: rgba(44,67,16,0.35);
  border-radius: 0.6rem; }
/* Space below the page title, before the panels */
div[data-testid="stElementContainer"]:has(.ow-title) { margin-bottom: 0.7rem; }
/* Equal height panels: each column fills its row, and the bordered panel
   (a layout wrapper directly in a column) fills the column */
div[data-testid="stColumn"] { display: flex; flex-direction: column; }
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] { flex: 1 1 auto; }
div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]
  > div[data-testid="stLayoutWrapper"] { flex: 1 1 auto; }
.ow-panel-title { font-size: 0.68rem !important; font-weight: 700;
                  text-transform: uppercase; letter-spacing: 0.06em;
                  color: var(--ow-dark) !important; margin: 0;
                  line-height: 1.4; margin-bottom: 0.8rem !important; }
.ow-footer { position: fixed; left: 0; right: 0; bottom: 0; z-index: 999;
             background: var(--ow-dark); color: #fff; font-size: 0.72rem;
             padding: 0.35rem 1rem; text-align: right; }
.ow-footer a { color: var(--ow-green); text-decoration: none; }
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="ow-title">OpenWorm 3D Viewer<span> 3D viewer'
        " for <i>C. elegans</i> models and datasets</span></p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ow-footer">OpenWorm 3D Viewer %s &middot; pyvista v%s, '
        "stpyvista v%s, streamlit v%s</div>"
        % (version, pv.__version__, stpyvista_version, st.__version__),
        unsafe_allow_html=True,
    )

# Distance between the worms: DEFAULT_SPACING, which the slider in Streamlit mode can lower

NEUROML_FILE = "NeuroML2/c302_D_Full.net.nml"


# The meshes of the models are read from the mesh caches (made by running the
# loaders with -cache, see meshcache.py; a CacheError is raised if they are
# missing), once, and then kept by Streamlit, so changing the cell selection only
# re-adds cells to a new plotter. They are not modified when adding them to a
# plotter, so sharing is safe.
def _cached(func):
    return st.cache_resource(show_spinner=True)(func) if st_mode else func


# The 3D models that can be shown (see models3d.py to add one)
models3d = Models3D(cache=_cached)


def get_cell_groups(nml_file):
    """Groups of cell names (present in the NeuroML file) to select from.
    An empty list means "all cells"."""

    import cect.Cells as cells

    ids = cells.ALL_PREFERRED_CELL_NAMES

    def present(names):
        return [i for i in ids if i in names]

    return {
        "All cells": [],
        "Only muscles": [i for i in ids if cells.is_known_muscle(i)],
        "Only neurons": [i for i in ids if cells.is_any_neuron(i)],
        "Sensory neurons": present(cells.SENSORY_NEURONS_COOK),
        "Interneurons": present(cells.INTERNEURONS_COOK),
        "Motor neurons": present(cells.MOTORNEURONS_COOK),
        "Pharyngeal neurons": present(cells.PHARYNGEAL_NEURONS),
        "Specific cells...": None,
    }, ids


def build_scene(
    selected,
    only_show=(),
    highlight=(),
    colors={},
    background=None,
    spacing=DEFAULT_SPACING,
):
    """Build a plotter containing the selected models (selected: dict of model key
    -> whether it is shown, see models3d.py)"""
    # Off-screen in Streamlit mode: the script runs on a non-main thread, where
    # on-screen rendering (e.g. Cocoa on macOS) aborts
    plotter = pv.Plotter(window_size=[800, 800], off_screen=st_mode)
    if background:
        plotter.set_background(background)

    models3d.add_to_plotter(
        plotter,
        SceneOptions(
            selected=selected,
            spacing=spacing,
            only_show=list(only_show),
            highlight=list(highlight),
            colors=colors,
        ),
    )

    plotter.add_axes()  # the xyz axes indicator
    plotter.set_viewup([0, 10, 0])
    return plotter


color_overlay = ColorOverlay()
COLOUR_OPTIONS = color_overlay.options  # the first is the default in the UI

# Background of the 3D view; green matches the page (OpenWorm green)
BACKGROUNDS = {"Green": "#9dbe45", "White": "white", "Black": "black"}

only_show = []
highlight = []
colour_option = COLOUR_OPTIONS[0]
background_option = "Green"
spacing = DEFAULT_SPACING
# model key -> shown; the checkboxes below override these defaults in Streamlit mode
selected_models = models3d.defaults()


# The Refresh button is disabled until an option in the form is changed. Changing
# a widget in a form doesn't rerun the script, so this can't be done in Python and
# is done in the browser: the state of the form (checkboxes, selections, slider...)
# is recorded when the page is first shown and after each Refresh, and the button
# is only enabled while the form is different from that.
REFRESH_GUARD_JS = """
<script>
(() => {
  if (window.__owRefreshGuard) return;  // the page's script persists over reruns
  window.__owRefreshGuard = true;

  const formState = (form) => {
    const parts = [];
    form.querySelectorAll('input').forEach((e) => {
      if (e.closest('[data-testid="stMultiSelect"]')) return;  // see its chips below
      parts.push(e.type === 'checkbox' ? e.checked : e.value);
    });
    form.querySelectorAll('[data-testid="stMultiSelect"]').forEach((e) =>
      parts.push(e.innerText));
    form.querySelectorAll('[aria-checked],[aria-pressed],[aria-valuenow]').forEach((e) =>
      parts.push(e.getAttribute('aria-checked') + e.getAttribute('aria-pressed') +
                 e.getAttribute('aria-valuenow')));
    return JSON.stringify(parts);
  };
  const refreshButton = (form) =>
    [...form.querySelectorAll('button')].find((b) => b.innerText.trim() === 'Refresh');

  let applied = null;  // the state of the form that is displayed
  let pending = null;
  let timer = null;
  const update = () => {
    const form = document.querySelector('[data-testid="stForm"]');
    const button = form && refreshButton(form);
    if (!button) return;
    const state = formState(form);
    if (applied === null) {
      // the first state: once the form has stopped changing while loading
      if (state !== pending) {
        pending = state;
        button.disabled = true;
        setTimeout(update, 500);
        return;
      }
      applied = state;
    }
    button.disabled = state === applied;
    if (!button.__owGuard) {
      button.__owGuard = true;
      // after Refresh, what is in the form is what is displayed
      button.addEventListener('click', () => setTimeout(() => {
        applied = formState(form);
        button.disabled = true;
      }, 100));
    }
  };
  // widgets are added/changed after the page loads, so look at every change (but
  // not too often)
  new MutationObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(update, 150);
  }).observe(document.body, {subtree: true, childList: true, attributes: true,
                             characterData: true});
  document.addEventListener('input', () => setTimeout(update, 150), true);
  document.addEventListener('click', () => setTimeout(update, 300), true);
  update();
})();
</script>
"""


def panel_title(text):
    st.markdown('<p class="ow-panel-title">%s</p>' % text, unsafe_allow_html=True)


if st_mode:
    groups, all_cell_ids = get_cell_groups(NEUROML_FILE)
    # the same groups as for showing, but none highlighted by default ("All cells"
    # highlighted would fade nothing)
    HIGHLIGHT_OPTIONS = ["None"] + [g for g in groups if g != "All cells"]

    # The controls are in a form, so the 3D view is only redisplayed when the
    # Refresh button (in Display Options) is pressed, not on every click
    with st.form("controls", border=False):
        # Control panels, in the order they are intended to be used:
        # what to show (Canvas), which cells (Subsets), colours (Overlay), Settings
        p_canvas, p_subsets, p_overlay, p_settings = st.columns([3, 3, 2, 2])

        with p_canvas.container(border=True):
            panel_title("3D Canvas")
            # the checkboxes of all the models, filling two columns across
            checkbox_cols = st.columns(2)
            selected_models = {
                m.key: checkbox_cols[n % 2].checkbox(
                    m.label,
                    value=m.default,
                    key="cb_" + m.key,
                    help=m.description,
                )
                for n, m in enumerate(models3d.models)
            }

        with p_subsets.container(border=True):
            panel_title("Select Subsets")
            show_label, show_col = st.columns([1, 2], vertical_alignment="center")
            show_label.markdown("Show")
            group = show_col.selectbox(
                "Cells to show",
                list(groups.keys()),
                key="sel_cell_group",
                label_visibility="collapsed",
                help="Which cells to show",
            )
            # Only shown (by the CSS above) when "Specific cells..." is chosen: in a
            # form the page doesn't update on a change, so Python can't do this
            chosen_cells = st.multiselect(
                "Specific cells to show",
                all_cell_ids,
                default=["AVAL", "AVAR"],
                key="sel_cells",
                label_visibility="collapsed",
            )
            only_show = chosen_cells if groups[group] is None else groups[group]

            hl_label, hl_col = st.columns([1, 2], vertical_alignment="center")
            hl_label.markdown("Highlight")
            hl_group = hl_col.selectbox(
                "Cells to highlight",
                HIGHLIGHT_OPTIONS,
                key="sel_highlight_group",
                label_visibility="collapsed",
                help="Cells to show as normal, with all the other shown cells "
                "made transparent (not yet implemented for Sibernetic)",
            )
            chosen_hl_cells = st.multiselect(
                "Specific cells to highlight",
                all_cell_ids,
                key="sel_hl_cells",
                placeholder="Choose cells to highlight",
                label_visibility="collapsed",
            )
            if hl_group == "Specific cells...":
                highlight = chosen_hl_cells
            elif hl_group != "None":
                highlight = groups[hl_group]

        with p_overlay.container(border=True):
            panel_title("Color Overlay")
            colour_option = st.selectbox(
                "Colours to use",
                COLOUR_OPTIONS,
                key="sel_colours",
                label_visibility="collapsed",
                help="Colours to use:\n"
                + "\n".join(
                    f"- {o}: {d}" for o, d in ColorOverlay.DESCRIPTIONS.items()
                ),
            )

        with p_settings.container(border=True):
            panel_title("Display Options")
            background_option = (
                st.segmented_control(
                    "Background",
                    list(BACKGROUNDS),
                    default="Green",
                    key="sel_background",
                    label_visibility="collapsed",
                    help="Background colour of the 3D view",
                )
                or "Green"  # nothing selected (clicking the active option deselects it)
            )
            label_col, slider_col = st.columns([1, 2], vertical_alignment="center")
            label_col.markdown("Worm spacing")
            spacing = slider_col.slider(
                "Worm spacing",
                min_value=0,
                max_value=DEFAULT_SPACING,
                value=DEFAULT_SPACING,
                key="sel_spacing",
                label_visibility="collapsed",
                help="Distance between the worms: lower values move them closer together",
            )
            st.form_submit_button(
                "Refresh",
                type="primary",
                width="stretch",
                help="Show the worms with the options chosen in all the panels. They "
                "are only applied when this is pressed, so several can be changed first.",
            )

if st_mode:
    st.html(REFRESH_GUARD_JS, unsafe_allow_javascript=True)

# Empty dict -> each model uses its own colors
colors = color_overlay.get_colors(colour_option, all_cell_ids if st_mode else [])

selection = dict(
    selected=selected_models,
    only_show=tuple(only_show),
    highlight=tuple(highlight),
    colors=colors,
    background=BACKGROUNDS[background_option] if st_mode else None,
    spacing=spacing,
)

if st_mode:
    try:
        with st.spinner("Loading worm models...", show_time=True):
            plotter = build_scene(**selection)
    except CacheError as e:
        st.error(str(e))
        st.stop()
else:
    plotter = build_scene(**selection)

print_("Created the scene...")

if st_mode:
    ##
    if True:
        print_("Pass a key to avoid re-rendering at each page change")
        from stpyvista import stpyvista

        # The key depends on the selection so the view is re-mounted (and so
        # updated) when a checkbox changes
        view_key = "pv_" + models3d.selection_key(selected_models)
        view_key += "_%d_%d_%s_%s" % (
            hash(tuple(only_show)),
            hash(tuple(highlight)),
            colour_option,
            background_option,
        )
        view_key += "_sp%d" % spacing

        with st.spinner(
            "Displaying worm models (slow first time a model is loaded)...",
            show_time=True,
        ):
            # The panel backend needs no extra dependencies (the default, trame, does)
            stpyvista(
                plotter,
                backend="panel",
                key=view_key,
                # the xyz axes indicator (plotter.add_axes() is not exported)
                backend_kwargs={"orientation_widget": True},
            )
            # The scene is exported to the browser by now. Close the plotter, as a
            # new one is built on every rerun and would otherwise be left holding
            # its render window and meshes.
            plotter.close()

            print_("Scene rendered in the browser (Streamlit mode).")
    pass
else:
    plotter.show()
