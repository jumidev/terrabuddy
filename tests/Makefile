SHELL := /bin/bash

setup:
	python3 -m venv venv
	source venv/bin/activate && pip uninstall terrabuddy -y
	source venv/bin/activate && cd ../tb && python3 setup.py install 
	source venv/bin/activate && pip install pytest


test_aws: setup
	source venv/bin/activate && python3 -m pytest aws_0*py

test: setup
	source venv/bin/activate && python3 -m pytest 0*py
