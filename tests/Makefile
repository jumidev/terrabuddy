SHELL := /bin/bash

test:
	python3 -m pytest *py

setup:
	python3 -m venv venv
	source venv/bin/activate && pip install -r ../tb/requirements.txt
	source venv/bin/activate && pip install pytest


test: setup
	source venv/bin/activate && python3 -m pytest *py
