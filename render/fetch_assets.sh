#!/bin/bash
# Downloads the CC0 "Human Base Meshes" bundle (Blender Studio) used for the on-hand renders.
set -e
cd "$(dirname "$0")/../extra" && mkdir -p render_assets && cd render_assets
curl -L -o hbm.zip https://download.blender.org/demo/asset-bundles/human-base-meshes/human-base-meshes-bundle-v1.4.1.zip
unzip -o -q hbm.zip && rm hbm.zip
