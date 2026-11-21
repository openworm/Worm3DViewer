# Witvliet2021

STL 3D models of the *C. elegans* adult nerve ring region (neurons, muscles and
glia), used by [witvliet2021.py](../witvliet2021.py) and the STL option of the
Streamlit app. The files are named `CELL-SEM_adult.stl`, e.g.
`ADAL-SEM_adult.stl`.

## Source

Witvliet, D., Mulcahy, B., Mitchell, J.K. et al.
**Connectomes across development reveal principles of brain maturation.**
*Nature* 596, 257-261 (2021). https://doi.org/10.1038/s41586-021-03778-8

The models are the file `Adult_neuron_3d_models.zip` of the Zenodo record
https://zenodo.org/records/5637219 (https://doi.org/10.5281/zenodo.5637219),
released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The
record says they were exported from a Blender workspace; the coordinate system
and units are not stated.

## Getting the files

The STL files (212, about 225 MB zipped) are not committed to this repository
(see `.gitignore` here). Run, from the main folder:

    ./download_witvliet2021.sh

This downloads the zip, checks it, copies just the `.stl` files into this
folder and removes the temporary files. Files already here are left alone.
