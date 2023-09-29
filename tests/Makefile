SHELL := /bin/bash

setup:
	python3 -m venv venv
	source venv/bin/activate && pip uninstall terrabuddy -y
	source venv/bin/activate && pip install -r requirements.txt
	source venv/bin/activate && cd ../tb && python3 setup.py install 

test_azurerm: setup
	source venv/bin/activate && python3 -m pytest azurerm_0*py

test_aws: setup
	source venv/bin/activate && python3 -m pytest aws_0*py

test_aws_last: setup
	source venv/bin/activate && python3 -m pytest aws_005*py

test: setup
	source venv/bin/activate && python3 -m pytest 0*py
