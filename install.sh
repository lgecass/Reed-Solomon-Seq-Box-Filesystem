#!/bin/bash
sudo apt update -y
sudo apt install meson ninja-build
pip install reedsolo
pip install meson
pip install pytest
git clone https://github.com/libfuse/libfuse.git
cd libfuse
mkdir build; cd build
meson setup ..
ninja
sudo ninja install
sudo apt-get install fuse3 libfuse3-dev -y
sudo apt-get install pkg-config -y

# Install creedsolo (reedsolomon c module) with options
pip install --upgrade reedsolo --no-binary "reedsolo" --no-cache --config-setting="--build-option=--cythonize" --use-pep517 --isolated --pre --verbose
pip install pyfuse3==3.2.3
