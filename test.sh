set -ex

ruff format *.py
ruff check *.py

python neuromlmodel.py -nogui 
python siberneticmodel.py -nogui 
python load.py -nogui 