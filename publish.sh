#!/bin/bash -x
#

if ! command -v poetry &>/dev/null; then
    pip3 install poetry
fi

poetry publish --build --skip-existing
