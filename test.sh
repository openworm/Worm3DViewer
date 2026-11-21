set -ex

# These will format and check the Python files in the current directory
ruff format *.py
ruff check *.py

# Test the NeuroML model loader, without showing the GUI
python neuromlmodel.py -nogui 

# Test the NeuroPAL (NeuroML model with NeuroPAL colored cells) without showing the GUI
python neuropal.py -nogui 

# Test the Sibernetic loader without showing the GUI
python SiberneticReplay.py Sibernetic/impermeability.txt -b -nogui 

# Test the VirtualWorm loader without showing the GUI
python virtualworm.py -nogui 

# Test the script for loading multiple 3D models, without showing the GUI
python load.py -nogui 

# Make the mesh caches (in ./cache) that the Streamlit app reads. The Witvliet
# et al. 2021 STL files are downloaded first (nothing is done if already there)
./download_witvliet2021.sh
python neuromlmodel.py -cache
python virtualworm.py -cache
python witvliet2021.py -cache
