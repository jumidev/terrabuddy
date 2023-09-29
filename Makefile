SHELL := /bin/bash

test:
	cd tests && make test

test_aws:
	cd tests && make test_aws

test_azurerm:
	cd tests && make test_azurerm

test_aws_last:
	cd tests && make test_aws_last

install:
	cd tb && make install
