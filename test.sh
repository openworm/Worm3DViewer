set -ex

# These will format and check the Python files in the current directory
ruff format *.py
ruff check *.py

# Test the NeuroML model loader, without showing the GUI
python neuromlmodel.py -nogui 

# Test the NeuroPAL (NeuroML model with NeuroPAL colored cells) without showing the GUI
python neuropal.py -nogui 

# Test the Sibernetic loader without showing the GUI
python siberneticmodel.py Sibernetic/impermeability.txt -b -nogui 

# Test the VirtualWorm loader without showing the GUI
python virtualworm.py -nogui 

# Test the script for loading multiple 3D models, without showing the GUI
python load.py -nogui 