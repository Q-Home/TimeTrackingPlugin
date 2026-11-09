#!/bin/bash
# LoxBerry invokes this hook as root; $6 is the extracted ZIP directory.
set -eu
archive_dir="${6:-$(dirname -- "$0")}"
home_dir="${LBHOMEDIR:-${5:-/opt/loxberry}}"
plugin_folder="${3:-timetrackingplugin}"
plugin_version="${4:-unknown}"
if ! command -v python3 >/dev/null 2>&1; then
    echo "<ERROR> Python 3 is required to preserve and activate this plugin update."
    exit 1
fi
python3 "$archive_dir/bin/plugin_lifecycle.py" finish \
    --home "$home_dir" --folder "$plugin_folder" \
    --archive "$archive_dir" --version "$plugin_version"
