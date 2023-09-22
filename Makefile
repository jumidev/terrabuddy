SHELL := /bin/bash

test:
	cd tests && make test

test_aws:
	cd tests && make test_aws
