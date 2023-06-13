#!/bin/bash
sudo apt install meson ninja-build
pip install -r requirements.txt

git clone https://github.com/libfuse/libfuse.git
cd libfuse
mkdir build; cd build
meson setup ..
ninja
sudo ninja install


# Install creedsolo (reedsolomon c module) with options
pip install --upgrade reedsolo --no-binary "reedsolo" --no-cache --config-setting="--build-option=--cythonize" --use-pep517 --isolated --pre --verbose
pip install pyfuse3==3.2.3
