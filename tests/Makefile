SHELL := /bin/bash

setup:
	python3 -m venv venv
	source venv/bin/activate && PYTHONWARNINGS=ignore pip uninstall cloudicorn -y
	source venv/bin/activate && PYTHONWARNINGS=ignore pip install -r requirements.txt
	source venv/bin/activate && PYTHONWARNINGS=ignore cd ../cli && python3 setup.py install 

test_azurerm: setup
	source venv/bin/activate && PYTHONWARNINGS=ignore python3 -m pytest azurerm_0*py

azurerm_delete_test_tfstate:
	az storage blob delete-batch  \
	--source $(TEST_AZURE_STORAGE_CONTAINER) \
	--account-name $(TEST_AZURE_STORAGE_ACCOUNT) \
	--account-key `az storage account keys list --account-name $(TEST_AZURE_STORAGE_ACCOUNT)  | jq  '.[0]["value"]' -r` 


test_aws: setup
	source venv/bin/activate && PYTHONWARNINGS=ignore python3 -m pytest aws_0*py

test_aws_last: setup
	source venv/bin/activate && python3 -m pytest `ls aws_*py | sort | tail -n 1`

test: setup
	source venv/bin/activate && python3 -m pytest 0*py

test_last: setup
	source venv/bin/activate && python3 -m pytest `ls 0*py | sort | tail -n 1`

