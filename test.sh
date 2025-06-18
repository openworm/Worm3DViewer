set -ex

ruff format *.py
ruff check *.py

python neuromlmodel.py -nogui 
python load.py -nogui 