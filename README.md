# Worm3DViewer

A 3D viewer for several _C. elegans_ models and datasets from the [OpenWorm](https://openworm.org) project, built with [PyVista](https://pyvista.org/) and deployed as a [Streamlit](https://streamlit.io/) web app. It is intended as a replacement for the OpenWorm Browser.

**Work in progress!**

<p align="center"><img src="images/someworms.gif"/></p>

It can show, side by side in one scene:

- **VirtualWorm** meshes of the body wall muscles (`bwm.obj`) and the neurons (`neurons.obj`), in one coordinate system (the muscles cover the body; choose neurons or muscles with the cell selection)
- **NeuroML** models of the worm: the c302 network (`NeuroML2/c302_D_Full.net.nml`) with morphologically detailed cells, the same network with just the cell somas (`c302_C2_Full.net.nml`), and the "canonical" positions of the neurons from Skuhersky et al. 2022 ("Toward a more accurate 3D atlas of C. elegans neurons") (`NeuroPAL_Canonical.net.nml`)
- the 3D models of the cells of the nerve ring region of an adult, from the electron microscopy of [Witvliet et al. (2021)](https://zenodo.org/records/5637219) (STL files, downloaded, see below)
- a **Sibernetic** simulation of the worm body: a replay of the particle positions (`Sibernetic/position_buffer.txt`)

## Running

Python 3.12 to 3.14 is tested (CI uses 3.12 and 3.14, the Docker image 3.13).

```bash
pip install -r requirements.txt
./test.sh                       # (or just the last three lines of it) downloads the Witvliet cells and builds the mesh caches
streamlit run app.py            # the web viewer
```

The web viewer does not build the meshes of the models: it reads **mesh caches** from `./cache` (one `.npz` per model, quick to load) and shows an error if one is missing. They are made by the `-cache` option of the loaders, which `./test.sh` and the Docker build run:

```bash
./download_witvliet2021.sh      # the STL files of the Witvliet et al. 2021 cells, into Witvliet2021/ (not in the repo; safe to rerun)
python models3d.py -cache       # the NeuroML models
python virtualworm.py -cache
python witvliet2021.py -cache
```

Rebuild them after changing what is baked into a cache (the NeuroML scale and rotation, the amount the Witvliet cells are decimated). The Sibernetic model is not cached.

With Docker:

```bash
./build.sh              # build the image (add -r for --no-cache) and open a shell in it
./runLocal.sh           # run the built image with a shell, port 8080 exposed
./stop.sh               # stop and remove the container
# The image's entrypoint is `streamlit run app.py` on port 8080
```

### Command line scripts

Each model can also be shown on its own in a desktop window:

```bash
python neuromlmodel.py          # a NeuroML network (default c302_D_Full.net.nml)
python neuropal.py              # NeuroPAL colored cells (somas only)
python virtualworm.py           # VirtualWorm muscle + neuron meshes
python witvliet2021.py          # the Witvliet et al. 2021 cells (click a cell to see its name)
python models3d.py              # list the 3D models of the web viewer
python SiberneticReplay.py Sibernetic/impermeability.txt   # Sibernetic replay
python load.py                  # all of the above in one scene
```

Add `-nogui` to any of them to load everything without opening a window. This is what the tests use.

## The web viewer

The first visit, with no options in the URL, shows a big title with some **example scenes** to choose from (the pictures and options are in `images/splash.json`). Clicking one sets the controls and shows it. Once a scene is shown, **More examples** (top right) goes back to them. The OpenWorm logo on the example screen links to [openworm.org](https://openworm.org).

The controls are in four panels above the 3D view, in the order they are intended to be used:

| Panel | Controls |
|---|---|
| **3D Canvas** | Which models to show: VirtualWorm, the NeuroML models, the Witvliet et al. 2021 cells, the Sibernetic model. Several can be shown at once, side by side |
| **Select Subsets** | **Show**: which cells to show: all cells, only muscles, only neurons, sensory neurons, interneurons, motor neurons, pharyngeal neurons, or "Specific cells..." for a list picked by name. **Highlight**: the same choices (and "None"): the highlighted cells are shown as normal and all the other shown cells are made transparent. The same cells are shown in each worm |
| **Color Overlay** | **WormAtlas cell colors** (the default) uses the standard WormAtlas colors by cell type, **WormAtlas + Sibernetic colors** also colors the muscles as in Sibernetic, **Default** uses the colors of each loaded model, and **Random** gives each named cell a random color (repeatable for a given name, never close to white, and the same in every model). With Random chosen, ticking **Shuffle colors** and pressing Refresh gives a new set of random colors (the box then unticks itself, and the new set stays until the next shuffle) |
| **Display Options** | Background color of the 3D view (green, white or black), the spacing between the worms (0 to 50: lower values move them closer together), and the **Refresh** button |

The controls only take effect when **Refresh** is pressed, so several can be changed first. It is disabled until something has changed. A spinner is shown while the scene is built.

The **What am I seeing?** button beside Refresh opens a summary between the controls and the 3D view: the description of each model shown, the list of the cells shown in it, and the settings (the button then says **Close**). It only shows or hides text made when the scene was built, so the 3D view stays as it is.

### Options in the URL

The options can be given in the URL, to return to a scene: for example

`?model3d=virtualworm,witvliet2021adult&show=Sensory neurons&highlight=AVAL,AVAR&color=random&background=white&spacing=30`

| Parameter | Value |
|---|---|
| `model3d` | Model keys (`virtualworm`, `neuroml_full`, `neuroml_somas`, `sibernetic`, `witvliet2021adult`, `canonical`), comma separated or repeated. Only these are shown |
| `show`, `highlight` | A group (as in the boxes, e.g. `only muscles`) or cell names, e.g. `AVAL,AVAR` (for "Specific cells...") |
| `color` | The start of a Color Overlay option: `wormatlas`, `wormatlas+sibernetic`, `default`, `random` (`colour` is also accepted) |
| `background` | `green`, `white` or `black` |
| `spacing` | A number from 0 to 50 |

Values that are not understood are ignored, with a warning. Choosing an example scene puts its options in the URL. The URL is not updated when the controls are changed.

Notes:

- Cell names are the standard names, e.g. `AVAL` for a neuron or `MDL01` for a body wall muscle.
- Subsets apply to all of the models. For the Sibernetic model only the muscles have names, so only muscle names select or color particles there (see below). Selecting a group with no muscles, such as the neurons, shows no Sibernetic particles, and highlighting is not supported there.
- The camera position is not kept when the scene is rebuilt.
- Large selections (all of the neurons, or the whole NeuroML model) take a few seconds to build and send tens of MB to the browser.

## Code structure

Each data source has its own module with an `add_*(plotter, ...)` function that adds geometry to a shared `pyvista.Plotter`, and an `if __name__ == "__main__"` block so it can be run alone. They all take the same optional arguments:

- `only_show`: a list of cell names to show; all other cells are omitted. An empty list (the default) shows everything.
- `colors`: a dict of cell name to color (a name, or an rgb tuple) used instead of the default color. Cells not in the dict (or an empty dict) keep their default color.
- `highlight`: a list of cell names to highlight: these are shown as normal and the other shown cells are made transparent. An empty list highlights nothing. (Not for Sibernetic.)

| File | Contents |
|---|---|
| `app.py` | The Streamlit app: the example scenes, the control panels, building the scene from the controls, and the page styling. The `-gui` argument runs the same scene in a desktop window instead |
| `models3d.py` | The list of 3D models the app can show (`Models3D.models`): each one's key, checkbox label and description, how to load its cached data, and how to place and add it. The NeuroML models (file, scale, rotation, cache) are in `NEUROML_MODELS`. `python models3d.py -cache` builds their caches |
| `coloroverlay.py` | The options of the Color Overlay panel: `ColorOverlay.get_colors(option, names)` returns the `colors` dict |
| `urlparams.py` | Reads the options given in the URL (and those of an example scene) as the initial values of the controls |
| `meshcache.py` | The fast on-disk cache of named meshes (`save_meshes()`, `load_meshes()`) used by the loaders' `-cache` option |
| `load.py` | The same models combined in a desktop (non-Streamlit) window |
| `neuromlmodel.py` | Generic NeuroML (not just _C. elegans_): `load_neuroml_model(file)` reads a file, `add_neuroml_model()` adds its cells, and `save_neuroml_cache()` / `load_neuroml_cache()` make and read a mesh cache for any file. The geometry of each cell is built once and kept, so adding it again is fast |
| `neuropal.py` | The NeuroML model with NeuroPAL colored cells (somas only) in a desktop window |
| `virtualworm.py` | `load_virtualworm()` reads the muscle and neuron meshes (one coordinate system); `add_virtualworm()` adds them; `-cache` builds their caches |
| `witvliet2021.py` | `load_stl_neurons()` reads the Witvliet et al. 2021 cell STL files (decimated, and cached by `-cache`); `add_stl_neurons()` adds them. Run alone, clicking a cell shows its name |
| `SiberneticReplay.py` | `add_sibernetic_model()`: a time series replay of Sibernetic output with play, rewind and fast forward buttons, a time slider, toggles for the particle types and charts of the muscle activation and body curvature |
| `SibSimulation.py` | The data layer for the replay (no GUI): reads `position_buffer.txt` and/or `report.json` from a Sibernetic run directory |
| `sibernetic_muscles.py` | Maps the named Sibernetic muscles to particles (see below) |
| `NeuroML2/` | The NeuroML model files (c302 networks, NeuroPAL, `cells/`) |
| `Sibernetic/` | Sample Sibernetic output and the muscle to particle map |
| `images/` | `splash.json` (the example scenes: an image and URL options each, and the text under the picture), their pictures and the logo |
| `Witvliet2021/` | The Witvliet et al. 2021 STL files, fetched by `download_witvliet2021.sh` (not in the repo) |
| `cache/` | The mesh caches (made by the `-cache` options; can be committed) |

Things worth knowing:

- **Loading and adding are separate.** The `load_*` functions read the files (or, for the app, the mesh caches) and return objects that the `add_*` functions only read from. In the Streamlit app each model's loader is wrapped in `st.cache_resource` (by `Models3D`), so each is read once and changing the cell selection only re-adds cells to a new plotter. The cache is shared by all browser sessions.
- **The mesh caches.** Building meshes (parsing OBJ and STL files, decimating, building NeuroML cells) is slow, so each loader's `-cache` option saves them in `cache/` as one `.npz` per model, which loads in milliseconds. A cache records the parameters it was built with, and loading it with others raises `CacheError`.
- **The 3D view.** The scene is shown with stpyvista using the `panel` backend, which needs no extra dependencies (the default `trame` backend does). Streamlit runs the script on a non-main thread, so the plotter is created off-screen, and it is closed after export because a new one is built on every rerun. The view is re-mounted when the selection changes, by including the selection in its key. `xvfb` is started on Linux when there is no display (the Docker image).
- **stpyvista cannot be imported outside Streamlit**, so scripts that run it standalone must not import it.
- **VirtualWorm meshes** (`bwm.obj`, about 25MB, and `neurons.obj`, about 100MB, both in the repo) are read by a small parser in `virtualworm.py` instead of trimesh. With trimesh 5, every object in `neurons.obj` came back with the name of the first, so the cell names were lost. A cell can be made of several objects (e.g. `MVL22_81`), and `only_show` and `colors` match the cell name without the number.
- **NeuroML coordinates** are rotated (`rotate_x/y/z`, degrees) and scaled (`factor`) to the viewer's frame; the values for each model are in `NEUROML_MODELS` in `models3d.py`. The canonical NeuroPAL positions are rotated, scaled and moved (`CANONICAL_TRANSLATE`) by a single fit to the 300 neurons that they share with c302, so they are not an exact match for each cell (median distance about 4.5 units).
- **Theme.** `.streamlit/config.toml` sets the color of selected controls to the dark green of the page. The rest of the look (green page, compact panels) is CSS in `app.py`.
- **Positioning.** Models are placed side by side using the `translate=` / `offset3d=` arguments, scaled by the spacing setting (see `models3d.py`: models that are not shown leave no gap).
- **The Refresh button.** The controls are in one `st.form`, so nothing reruns until Refresh is pressed. Showing the specific cells pickers only for "Specific cells..." and disabling Refresh until something has changed are done in the browser (CSS and a little JavaScript in `app.py`).

### Sibernetic muscles

In a Sibernetic configuration a muscle is not a set of particles but a set of elastic connections tagged with a muscle id (1 to 96, in four quadrants of 24 muscles named MDR, MVR, MVL and MDL, 01 to 24). `sibernetic_muscles.py` works out the particles of each named muscle from a configuration file:

```bash
python sibernetic_muscles.py CONFIGURATION_FILE -o muscles.json
```

The result for `worm_alone_half_resolution` is in `Sibernetic/muscle_particles_worm_alone_half_resolution.json`, and `add_sibernetic_model()` uses it for `only_show` and `colors`. The module documentation there explains how this was derived from the Sibernetic C++, and has a list of **open issues**. The main ones are that it has not been established which end of the body row 01 is at (head or tail), which side is left, and that only that one configuration has been checked.

## Tests and CI

There is no pytest. `./test.sh` is the test suite: it runs `ruff format` and `ruff check` and then each loader script with `-nogui` as a smoke test (to run a single test, run the script on its own with `-nogui`). It finishes by downloading the Witvliet et al. 2021 cells and building the mesh caches (`-cache`). Keep the `-nogui` / `-gui` handling in scripts, as it keeps them testable without a display.

GitHub workflows:

- `non_omv.yml`: Python 3.12 and 3.14, `pip install -r requirements.txt` then `./test.sh`
- `docker-image.yml`: runs `./build.sh`. The Dockerfile downloads the Witvliet cells and builds the mesh caches, so the image has what the app reads
- `omv-ci.yml`: validates the NeuroML2 files with OMV (`osb-model-validation`) and the `jNeuroML_validate` engine

The Streamlit app itself is not covered by `test.sh`. It can be exercised without a browser with Streamlit's `streamlit.testing.v1.AppTest`.
