set -ex

ruff format *.py
ruff check *.py

python neuromlmodel.py -nogui 
python neuropal.py -nogui 

python siberneticmodel.py -nogui 
python virtualworm.py -nogui 
python load.py -nogui 