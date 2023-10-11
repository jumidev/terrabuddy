SHELL := /bin/bash

install: uninstall
	python3 setup.py install --user
	rm -rf build dist *egg-info

uninstall:
	pip3 uninstall terrabuddy -y

