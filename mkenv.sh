#!/usr/bin/bash
rm -rf env
python -m venv env
source env/bin/activate
pip install --require-virtualenv --upgrade pip
pip install --require-virtualenv --upgrade --requirement requirements.txt

