#!/usr/bin/env bash
#
# Download the adult neuron 3D models (STL files) of
#
#   Witvliet et al. (2021) Connectomes across development reveal principles of
#   brain maturation. Nature 596, 257-261. https://doi.org/10.1038/s41586-021-03778-8
#
# from https://zenodo.org/records/5637219 (CC BY 4.0) and put just the .stl
# files in the folder Witvliet2021 (next to this script, or the folder given as
# the first argument).
#
# Safe to run more than once: files already in the folder are left alone (and
# nothing is downloaded if all of them are there). Temporary files are removed
# when the script ends.
#
# Usage:  ./download_witvliet2021.sh [output_folder]

set -euo pipefail

URL="https://zenodo.org/records/5637219/files/Adult_neuron_3d_models.zip?download=1"
MD5="885f3457aaf849279ac61810d3e9c1c5"  # of the zip, from the Zenodo record
EXPECTED_STL_FILES=212                   # in the zip

OUT_DIR="${1:-$(cd "$(dirname "$0")" && pwd)/Witvliet2021}"

count_stl() { find "$OUT_DIR" -maxdepth 1 -name '*.stl' 2>/dev/null | wc -l | tr -d ' '; }

mkdir -p "$OUT_DIR"

if [ "$(count_stl)" -ge "$EXPECTED_STL_FILES" ]; then
    echo "$OUT_DIR already has $(count_stl) STL files; nothing to do"
    exit 0
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/witvliet2021.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Downloading Adult_neuron_3d_models.zip (about 225 MB)..."
curl -fL --progress-bar -o "$TMP_DIR/models.zip" "$URL"

# Check the download, if there is a tool to do it
if command -v md5sum >/dev/null 2>&1; then
    ACTUAL="$(md5sum "$TMP_DIR/models.zip" | cut -d' ' -f1)"
elif command -v md5 >/dev/null 2>&1; then
    ACTUAL="$(md5 -q "$TMP_DIR/models.zip")"
else
    ACTUAL="$MD5"
    echo "No md5sum/md5 found: not checking the download"
fi
if [ "$ACTUAL" != "$MD5" ]; then
    echo "ERROR: checksum of the download is $ACTUAL, expected $MD5" >&2
    exit 1
fi

echo "Unzipping..."
unzip -q "$TMP_DIR/models.zip" -d "$TMP_DIR/unzipped"

# Just the .stl files: skip the macOS __MACOSX folder (and its ._ files)
ADDED=0
SKIPPED=0
while IFS= read -r -d '' f; do
    target="$OUT_DIR/$(basename "$f")"
    if [ -e "$target" ]; then
        SKIPPED=$((SKIPPED + 1))
    else
        cp "$f" "$target"
        ADDED=$((ADDED + 1))
    fi
done < <(find "$TMP_DIR/unzipped" -name '*.stl' -not -name '._*' \
            -not -path '*/__MACOSX/*' -print0)

echo "Added $ADDED STL files to $OUT_DIR ($SKIPPED already there)"
# the temporary files are removed by the trap
