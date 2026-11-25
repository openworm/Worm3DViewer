from coloroverlay import ColorOverlay
from meshcache import CacheError
from models3d import DEFAULT_SPACING, Models3D, SceneOptions

import os
import re
import platform
import shutil
import subprocess
import sys

import cect.Cells as cect_cells

import pyvista as pv

import urlparams

version = "v0.4.1"

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
.ow-header { display: flex; justify-content: space-between; align-items: center; }
/* the logo is as high as the title (its font size * its line height of 1.5) */
.ow-logo img { height: 1.875rem; display: block; }
.ow-header:has(.ow-title-big) .ow-logo img { height: 3rem; }
/* "More examples": at the right of the title row, as high as the title */
.st-key-more_examples { width: 100%; }
.st-key-more_examples [data-testid="stButton"] { display: flex; justify-content: flex-end; }
div[data-testid="stHorizontalBlock"]:has(.st-key-more_examples) { margin-bottom: 0.7rem; }
div[data-testid="stHorizontalBlock"]:has(.st-key-more_examples)
  div[data-testid="stElementContainer"]:has(.ow-title) { margin-bottom: 0; }
/* (Streamlit would make the title's box shorter than the title) */
div[data-testid="stHorizontalBlock"]:has(.st-key-more_examples)
  [data-testid="stElementContainer"]:has(.ow-title),
div[data-testid="stHorizontalBlock"]:has(.st-key-more_examples)
  [data-testid="stElementContainer"]:has(.ow-title) [data-testid="stMarkdown"],
div[data-testid="stHorizontalBlock"]:has(.st-key-more_examples)
  [data-testid="stElementContainer"]:has(.ow-title) [data-testid="stMarkdown"] > div {
  min-height: 1.875rem; height: auto; }
.ow-header, [data-testid="stMarkdownContainer"]:has(.ow-header) { margin-bottom: 0; }
.st-key-more_examples button { min-height: 1.875rem; padding: 0 0.9rem; }
/* The "What am I seeing?" button (beside Refresh) and the summary it shows/hides, in
   the browser: the page's class ow-summary-open is toggled by SUMMARY_JS */
.ow-summary-toggle { width: 100%; min-height: 2.5rem; border-radius: 0.5rem;
  border: 1px solid rgba(44,67,16,0.35); background: rgba(255,255,255,0.75);
  color: var(--ow-text); font: inherit; font-size: 0.78rem; cursor: pointer; }
.ow-summary-toggle:hover { background: #fff; }
.ow-summary-toggle .when-open, html.ow-summary-open .ow-summary-toggle .when-closed {
  display: none; }
html.ow-summary-open .ow-summary-toggle .when-open { display: inline; }
.ow-summary { display: none; }
html.ow-summary-open .ow-summary { display: block; padding: 0.6rem 0.9rem;
  background: #fff; border: 1px solid rgba(44,67,16,0.35);
  border-radius: 0.6rem; color: var(--ow-text); font-size: 0.78rem; line-height: 1.4; }
.ow-summary p { margin: 0 0 0.35rem 0; font-size: 0.78rem; }
.ow-summary .ow-summary-title { font-size: 0.68rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.06em; color: var(--ow-dark); }
.ow-summary h5 { margin: 0.5rem 0 0.15rem 0; font-size: 0.82rem; color: var(--ow-dark); }
.ow-summary .cells a { text-decoration: none; }
.ow-summary .cells { max-height: 5.5rem; overflow-y: auto; }
.ow-title span { font-size: 0.75rem; font-weight: 400; margin-left: 0.6rem;
                 opacity: 0.9; }
.stApp p.ow-title-big { font-size: 2rem; }
.ow-title-big span { font-size: 0.9rem; }
.ow-splash-hint { font-size: 0.85rem !important; margin: 0.2rem 0 0.5rem 0 !important; }
/* A splash scene: its picture and name, with the (invisible) button over all of it */
div[class*="st-key-splash_card_"] { flex: 0 0 auto !important; position: relative;
  border: 1px solid rgba(44,67,16,0.35); border-radius: 0.6rem;
  overflow: hidden; background: rgba(255,255,255,0.22); cursor: pointer;
  transition: transform 0.12s, box-shadow 0.12s; }
div[class*="st-key-splash_card_"] > div { flex: 0 0 auto; }
/* (Streamlit would shrink the name's box to less than its text, clipping it) */
div[class*="st-key-splash_card_"] [data-testid="stMarkdown"],
div[class*="st-key-splash_card_"] [data-testid="stMarkdown"] > div {
  min-height: 2.6rem; height: auto; }
div[class*="st-key-splash_card_"]:hover { transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
div[class*="st-key-splash_card_"] p { padding: 0 0.4rem 0.3rem 0.4rem; font-weight: 600;
  overflow: hidden; display: -webkit-box; -webkit-box-orient: vertical;
  -webkit-line-clamp: 2; line-height: 1.3; }
div[class*="st-key-splash_btn_"] { position: absolute; inset: 0; z-index: 2;
  width: 100% !important; height: 100% !important; }
div[class*="st-key-splash_btn_"] [data-testid="stButton"],
div[class*="st-key-splash_btn_"] [data-testid="stTooltipHoverTarget"],
div[class*="st-key-splash_btn_"] [data-testid="stTooltipIcon"],
div[class*="st-key-splash_btn_"] [data-testid="stTooltipIcon"] > div,
div[class*="st-key-splash_btn_"] [data-testid="stButton"] div {
  width: 100%; height: 100%; }
div[class*="st-key-splash_btn_"] button { width: 100%; height: 100%; opacity: 0;
  cursor: pointer; }
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
/* "Shuffle colors" is only shown when the random colors are chosen */
.st-key-sel_shuffle { display: none; }
div[data-testid="stVerticalBlock"]:has(.st-key-sel_colors input[value="Random color per cell"])
  > .st-key-sel_shuffle { display: block; }
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
        '<div class="ow-footer">OpenWorm 3D Viewer %s &middot; pyvista v%s, '
        "stpyvista v%s, streamlit v%s</div>"
        % (version, pv.__version__, stpyvista_version, st.__version__),
        unsafe_allow_html=True,
    )


# The meshes of the models are read from the mesh caches (made by running the
# loaders with -cache, see meshcache.py; a CacheError is raised if they are
# missing), once, and then kept by Streamlit, so changing the cell selection only
# re-adds cells to a new plotter. They are not modified when adding them to a
# plotter, so sharing is safe.
def _cached(func):
    return st.cache_resource(show_spinner=True)(func) if st_mode else func


# The 3D models that can be shown (see models3d.py to add one)
models3d = Models3D(cache=_cached)


def get_cell_groups():
    """Groups of cell names to select from.
    An empty list means "all cells"."""

    import cect.Cells as cells

    ids = cells.ALL_PREFERRED_CELL_NAMES

    def present(names):
        return [i for i in ids if i in names]

    return {
        "All cells": [],
        "Only muscles": [i for i in ids if cells.is_known_muscle(i)],
        "Only neurons": [i for i in ids if cells.is_any_neuron(i)],
        "All except neurons & muscles": [
            i
            for i in ids
            if not cells.is_any_neuron(i) and not cells.is_known_muscle(i)
        ],
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
COLOR_OPTIONS = color_overlay.options  # the first is the default in the UI

# Background of the 3D view; green matches the page (OpenWorm green)
BACKGROUNDS = {"Green": "#9dbe45", "White": "white", "Black": "black"}

only_show = []
highlight = []
color_option = COLOR_OPTIONS[0]
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

  let lastScene = null;
  let applied = null;  // the state of the form that is displayed
  let pending = null;
  let timer = null;
  const update = () => {
    const form = document.querySelector('[data-testid="stForm"]');
    const button = form && refreshButton(form);
    if (!button) return;
    // a scene was chosen from the splash: its options are what is displayed
    const marker = document.querySelector('[data-ow-scene]');
    const scene = marker ? marker.dataset.owScene : null;
    if (scene !== lastScene) {
      lastScene = scene;
      applied = null;
      pending = null;
    }
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


SPLASH_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "images", "splash.json"
)
SPLASH_COLUMNS = 6  # scenes per row (a layout for six; more wrap onto more rows)
SPLASH_THUMB_WIDTH = 480  # pixels: the pictures are scaled down for the browser


LOGO_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "images", "OpenWormLogo.png"
)
LOGO_URL = "https://openworm.org"


@st.cache_data(show_spinner=False)
def _logo_data_uri(modified):
    import base64

    with open(LOGO_FILE, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def logo_html():
    """The OpenWorm logo as a link to openworm.org (opened in a new tab); empty if
    there is no logo file"""
    if not os.path.isfile(LOGO_FILE):
        return ""
    return (
        '<a class="ow-logo" href="%s" target="_blank" rel="noopener noreferrer" '
        'title="OpenWorm"><img src="%s" alt="OpenWorm"></a>'
        % (LOGO_URL, _logo_data_uri(os.path.getmtime(LOGO_FILE)))
    )


def end_splash():
    """Callback of Refresh: the splash is not shown any more. And if "Shuffle colors"
    was ticked (for the random colors) a new set of random colors is used from now
    on, and the box is unticked."""
    st.session_state.splash_open = False
    if st.session_state.get("sel_shuffle"):
        if st.session_state.get("sel_colors") == ColorOverlay.RANDOM:
            import random

            st.session_state.color_seed = random.randrange(1, 2**31)
        st.session_state.sel_shuffle = False
        # what is displayed is what is in the form again (see the guard in the page)
        st.session_state.scene_token = st.session_state.get("scene_token", 0) + 1


def open_splash():
    """Callback of "More examples": show the splash scenes again (and, as the options
    are not those of a scene any more, no options in the URL)"""
    st.session_state.splash_open = True
    st.query_params.clear()


def choose_scene(scene):
    """Callback of a splash scene: load it, i.e. set the controls to its options (in
    the next run) and put them in the URL"""
    st.session_state.splash_open = False
    st.session_state.pending_scene = scene
    st.session_state.scene_token = st.session_state.get("scene_token", 0) + 1
    st.query_params.clear()
    st.query_params.update(
        {k: str(v) for k, v in scene.items() if k not in ("image", "text")}
    )


@st.cache_data(show_spinner=False)
def _thumbnail(path, modified):
    """The JPEG bytes of a scene's picture, scaled down (modified: for the cache)"""
    import io

    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        # cropped to 16:9 (from the middle), so all the scenes are the same size
        w, h = im.size
        if w * 9 > h * 16:
            x = (w - h * 16 // 9) // 2
            im = im.crop((x, 0, w - x, h))
        else:
            y = (h - w * 9 // 16) // 2
            im = im.crop((0, y, w, h - y))
        im.thumbnail((SPLASH_THUMB_WIDTH, SPLASH_THUMB_WIDTH))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=85)
        return out.getvalue()


def make_splash(active):
    """The function that shows the splash scenes of images/splash.json (read each
    time it is shown): a picture each, with the options of a scene (the same names as
    the URL's: model3d, show, highlight, color, background, spacing) and the "text"
    to show under the picture (default: the names of its models); clicking one
    loads it."""

    def show():
        import json

        try:
            with open(SPLASH_FILE) as f:
                scenes = json.load(f)["options"]
        except (OSError, ValueError, KeyError) as e:
            print_("No splash scenes (%s: %s)" % (SPLASH_FILE, e))
            return
        st.markdown(
            '<p class="ow-splash-hint">Choose a scene to start with, or set the '
            "options below and press Refresh.</p>",
            unsafe_allow_html=True,
        )
        labels = {m.key: m.label for m in models3d.models}
        descriptions = {m.key: m.description for m in models3d.models}
        for row in range(0, len(scenes), SPLASH_COLUMNS):
            cols = st.columns(SPLASH_COLUMNS)
            for n, scene in enumerate(scenes[row : row + SPLASH_COLUMNS]):
                i = row + n
                path = os.path.join(
                    os.path.dirname(SPLASH_FILE), scene.get("image", "")
                )
                title = scene.get("text") or ", ".join(
                    labels.get(k.strip(), k.strip())
                    for k in str(scene.get("model3d", "")).split(",")
                )
                # the hover text: the description of each model of the scene
                hover = "\n\n".join(
                    "**%s**: %s" % (labels[k], descriptions[k])
                    for k in (
                        k.strip() for k in str(scene.get("model3d", "")).split(",")
                    )
                    if k in descriptions
                )
                with cols[n].container(key="splash_card_%d" % i):
                    if os.path.isfile(path):
                        st.image(
                            _thumbnail(path, os.path.getmtime(path)), width="stretch"
                        )
                    st.markdown(title)
                    st.button(
                        title,
                        key="splash_btn_%d" % i,
                        help=hover or title,
                        on_click=choose_scene,
                        args=(scene,),
                    )

    return show


SUMMARY_JS = """
<script>
(() => {
  if (window.__owSummaryToggle) return;  // the page's script persists over reruns
  window.__owSummaryToggle = true;
  // the state is a class of the page, so it stays when the controls are redisplayed
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.ow-summary-toggle')) return;
    e.preventDefault();
    document.documentElement.classList.toggle('ow-summary-open');
  }, true);
})();
</script>
"""

MAX_LISTED_CELLS = 1100  # (all the cells of any of the models fit)


CELL_LINK_BASE = "https://openworm.org/ConnectomeToolbox/Cells/index.html#"


def cell_link(cell, color):
    """HTML for a cell's name as a link to its page of the Connectome Toolbox, opened
    in a new tab, in `color` (that of the cell in the scene). Just the name if it is
    not a standard cell."""
    from html import escape

    try:
        link = cect_cells.get_cell_internal_link(
            cell, html=True, use_color=False, text=cell
        )
    except Exception:  # not a cell that the toolbox knows
        return escape(cell)
    link = link.replace("<a ", '<a style="color:%s" ' % escape(color), 1)
    # (the toolbox's links are relative to its own pages)
    link = link.replace("../Cells/index.html#", CELL_LINK_BASE)
    return link.replace("<a ", '<a target="_blank" rel="noopener noreferrer" ', 1)


def markdown_to_html(text):
    """The little markdown of the descriptions of the models ([text](url) links and
    _italics_) as HTML, with everything else escaped. Links open in a new tab."""
    from html import escape

    html = escape(text, quote=False)
    html = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        html,
    )
    return re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<i>\1</i>", html)


def cell_color_fallback(cell, colors):
    """The color of a cell that is in none of the models shown (e.g. a highlighted
    cell that they do not have): its overlay color, else its WormAtlas one"""
    from virtualworm import get_color_for_object

    return pv.Color(colors.get(cell) or get_color_for_object(cell)).hex_rgb


def html_links_to_markdown(text):
    """<a href="url">text</a> -> [text](url), for the places that show markdown"""
    return re.sub(r'<a href="([^"]*)">(.*?)</a>', r"[\2](\1)", text)


def scene_summary_html(selected, only_show, highlight, settings, colors=None):
    """HTML describing the scene: the description of each model shown and the list of
    the cells shown in it, and the settings. It is made on each run and hidden until
    the "What am I seeing?" button is clicked."""
    from html import escape

    shown = [m for m in models3d.models if selected.get(m.key)]
    parts = [
        '<div class="ow-summary"><p class="ow-summary-title">What am I seeing?</p>'
    ]
    if not shown:
        parts.append("<p>No 3D models are selected.</p>")
    for m in shown:
        parts.append(
            "<h5>%s</h5><p>%s</p>" % (escape(m.label), markdown_to_html(m.description))
        )
        cells = models3d.shown_cells(m.key, only_show)
        if cells is None:
            parts.append(
                "<p><i>The particles of the simulated body. Only its muscles have "
                "names, so only muscles can be selected.</i></p>"
            )
        elif not cells:
            parts.append("<p><i>None of the selected cells are in this model.</i></p>")
        else:
            cell_color = models3d.cell_colors(m.key, cells[:MAX_LISTED_CELLS], colors)
            parts.append(
                '<p class="cells"><b>%d cells shown:</b> %s</p>'
                % (
                    len(cells),
                    # (the links are HTML already: only the cell names are escaped)
                    ", ".join(
                        cell_link(c, cell_color[c]) for c in cells[:MAX_LISTED_CELLS]
                    ),
                )
            )
    shown_in = "all cells" if not only_show else "%d chosen cells" % len(only_show)
    parts.append("<br/><p>Showing %s (%s).</p>" % (shown_in, escape(settings["show"])))
    if highlight:
        # each in its color in the scene, which is that of the first model shown that
        # has the cell
        hl_color = {}
        for m in shown:
            in_model = models3d.shown_cells(m.key, highlight) or []
            for cell, color in models3d.cell_colors(m.key, in_model, colors).items():
                hl_color.setdefault(cell, color)
        links = ", ".join(
            cell_link(c, hl_color.get(c) or cell_color_fallback(c, colors))
            for c in highlight[:MAX_LISTED_CELLS]
        )
        parts.append(
            '<br/><p class="cells"><b>Highlighting %d cells (%s)</b>, the other cells are '
            "transparent: %s</p>"
            % (len(highlight), escape(settings["highlight"]), links)
        )
    color = settings["color"]
    description = ColorOverlay.DESCRIPTIONS.get(color, "")
    parts.append(
        "<p>Colors: <b>%s</b>%s</p></div>"
        % (
            escape(color),
            # (the descriptions are our own HTML: links are opened in a new tab)
            ": " + description.replace("<a ", '<a target="_blank" rel="noopener" ')
            if description
            else "",
        )
    )
    return "".join(parts)


def panel_title(text):
    st.markdown('<p class="ow-panel-title">%s</p>' % text, unsafe_allow_html=True)


# The first visit (no options in the URL): the title is bigger, with the splash scenes
# to choose from, until one is chosen (or Refresh is pressed)
if st_mode and "splash_open" not in st.session_state:
    st.session_state.splash_open = not st.query_params  # (the first visit)
splash_active = st_mode and st.session_state.splash_open

if st_mode:
    header = (
        '<div class="ow-header"><p class="ow-title%s">OpenWorm 3D Viewer<span> 3D '
        "viewer for <i>C. elegans</i> models and datasets</span></p>%s</div>"
    )
    if splash_active:
        # the logo, which links to openworm.org
        st.markdown(header % (" ow-title-big", logo_html()), unsafe_allow_html=True)
    else:
        # a button to go back to the splash scenes, where the logo was
        title_col, more_col = st.columns([5, 1], vertical_alignment="center")
        title_col.markdown(header % ("", ""), unsafe_allow_html=True)
        more_col.button(
            "More examples",
            key="more_examples",
            type="primary",
            on_click=open_splash,
            help="Go back to the example scenes to choose from",
        )
    if splash_active:
        make_splash(True)()
    groups, all_cell_ids = get_cell_groups()
    # the same groups as for showing, but none highlighted by default ("All cells"
    # highlighted would fade nothing)
    HIGHLIGHT_OPTIONS = ["None"] + [g for g in groups if g != "All cells"]

    # The controls are in a form, so the 3D view is only redisplayed when the
    # Refresh button (in Display Options) is pressed, not on every click
    # Options given in the URL (e.g. ?model3d=sibernetic) replace the defaults of
    # the widgets when the page is first opened
    def options_of(get):
        return urlparams.Options(
            get,
            models3d,
            list(groups),
            HIGHLIGHT_OPTIONS,
            all_cell_ids,
            COLOR_OPTIONS,
            BACKGROUNDS,
            DEFAULT_SPACING,
        )

    init = options_of(st.query_params.get_all)
    if init.problems:
        st.warning(
            "Not all of the options in the URL were used: " + "; ".join(init.problems)
        )

    # A splash scene was clicked (see the top of the page): set the controls to
    # its options, before the widgets are made
    scene = st.session_state.pop("pending_scene", None)
    if scene:
        chosen = options_of(lambda name: [str(scene[name])] if name in scene else [])
        st.session_state.update(chosen.widget_values(models3d))
        init = chosen
    # (the widgets get their first values from the session state, not defaults)
    for key, value in init.widget_values(models3d).items():
        st.session_state.setdefault(key, value)

    with st.form("controls", border=False):
        # Control panels, in the order they are intended to be used:
        # what to show (Canvas), which cells (Subsets), colors (Overlay), Settings
        p_canvas, p_subsets, p_overlay, p_settings = st.columns([3, 3, 2, 2])

        with p_canvas.container(border=True):
            panel_title("3D Canvas")
            # the checkboxes of all the models, filling two columns across
            checkbox_cols = st.columns(2)
            selected_models = {
                m.key: checkbox_cols[n % 2].checkbox(
                    m.label,
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
            color_option = st.selectbox(
                "Colors to use",
                COLOR_OPTIONS,
                key="sel_colors",
                label_visibility="collapsed",
                help="Colors to use:\n"
                + "\n".join(
                    f"- {o}: {html_links_to_markdown(d)}"
                    for o, d in ColorOverlay.DESCRIPTIONS.items()
                ),
            )
            st.checkbox(
                "Shuffle colors",
                key="sel_shuffle",
                help="Use a new set of random colors when Refresh is pressed",
            )

        with p_settings.container(border=True):
            panel_title("Display Options")
            background_option = (
                st.segmented_control(
                    "Background",
                    list(BACKGROUNDS),
                    key="sel_background",
                    label_visibility="collapsed",
                    help="Background color of the 3D view",
                )
                or "Green"  # nothing selected (clicking the active option deselects it)
            )
            label_col, slider_col = st.columns([1, 2], vertical_alignment="center")
            label_col.markdown("Worm spacing")
            spacing = slider_col.slider(
                "Worm spacing",
                min_value=0,
                max_value=DEFAULT_SPACING,
                key="sel_spacing",
                label_visibility="collapsed",
                help="Distance between the worms: lower values move them closer together",
            )
            refresh_col, summary_col = st.columns(2)
            refresh_col.form_submit_button(
                "Refresh",
                on_click=end_splash,
                type="primary",
                width="stretch",
                help="Show the worms with the options chosen in all the panels. They "
                "are only applied when this is pressed, so several can be changed first.",
            )
            # (not a Streamlit button: it only shows/hides the summary in the
            # browser, with no rerun, so the 3D view stays; see SUMMARY_JS)
            summary_col.html(
                '<button type="button" class="ow-summary-toggle">'
                '<span class="when-closed">What am I seeing?</span>'
                '<span class="when-open">Close</span></button>'
            )

if st_mode:
    st.html(REFRESH_GUARD_JS, unsafe_allow_javascript=True)
    if "scene_token" in st.session_state:  # (for the guard: see above)
        st.markdown(
            '<div data-ow-scene="%d" hidden></div>' % st.session_state.scene_token,
            unsafe_allow_html=True,
        )
    if splash_active:
        # The first visit: wait for a scene to be chosen (or Refresh pressed)
        st.stop()

# Empty dict -> each model uses its own colors
color_seed = st.session_state.get("color_seed", 0) if st_mode else 0
colors = color_overlay.get_colors(
    color_option, all_cell_ids if st_mode else [], color_seed
)

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
        summary = scene_summary_html(
            selected_models,
            only_show,
            highlight,
            dict(
                show=group,
                highlight=hl_group,
                color=color_option,
                background=background_option,
                spacing=spacing,
            ),
            colors,
        )
    except CacheError:
        summary = ""  # (the error is shown below)
    # Shown or hidden by the "What am I seeing?" button, in the browser
    st.html(summary + SUMMARY_JS, unsafe_allow_javascript=True)

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
            color_option,
            background_option,
        )
        view_key += "_sp%d_cs%d" % (spacing, color_seed)

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
