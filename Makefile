SHELL := /bin/bash

test:
	cd tests && make test

test_last:
	cd tests && make test_last

test_aws:
	cd tests && make test_aws

test_azurerm:
	cd tests && make test_azurerm

test_aws_last:
	cd tests && make test_aws_last

install:
	cd tb && make install

build_test_docker:
	docker build . -f Dockerfile-tests -t test-terrabuddy
	
test_docker: build_test_docker
	docker run -it test-terrabuddy

publish_pypi:
	cd tb && rm -rf dist build && \
	python3 setup.py sdist bdist_wheel && \
	python3 -m twine upload dist/*