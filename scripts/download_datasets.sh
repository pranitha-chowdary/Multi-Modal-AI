#!/usr/bin/env bash
# Guidance script for acquiring ADIS datasets. Most sources require manual
# registration/approval, so this script prints instructions rather than
# silently downloading anything on your behalf. See docs/datasets.md for
# full context on each dataset and how it's used.
set -euo pipefail

DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data/raw"

echo "ADIS dataset acquisition guide"
echo "=============================="
echo "Target directory: ${DATA_DIR}"
echo
echo "1) xBD (xView2 building damage)"
echo "   - Register/download from the official xView2 challenge site."
echo "   - Place extracted data under: ${DATA_DIR}/xbd/"
echo
echo "2) FloodNet (flood segmentation)"
echo "   - Download from the official FloodNet challenge/release page."
echo "   - Place extracted data under: ${DATA_DIR}/floodnet/"
echo
echo "3) CrisisNLP (crisis social media text)"
echo "   - Register/download from the CrisisNLP (QCRI) portal."
echo "   - Place extracted data under: ${DATA_DIR}/crisisnlp/"
echo
echo "4) Andhra Pradesh regional dataset"
echo "   - To be curated per docs/datasets.md; place under: ${DATA_DIR}/ap_regional/"
echo
echo "Each of the above requires manual registration/consent handling and is"
echo "NOT auto-downloaded by this script. Once downloaded, re-run this script"
echo "to verify the expected directory layout:"
echo

mkdir -p "${DATA_DIR}"/{xbd,floodnet,crisisnlp,ap_regional}

for name in xbd floodnet crisisnlp ap_regional; do
  dir="${DATA_DIR}/${name}"
  if [ -z "$(ls -A "${dir}" 2>/dev/null)" ]; then
    echo "  [ ] ${dir} (empty — dataset not yet placed here)"
  else
    echo "  [x] ${dir} (contains files)"
  fi
done
