#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, shutil
import unittest
from tbcore import Project, TfStateStoreAwsS3, WrongPasswordException
from tbcore import assert_azurerm_sp_creds, get_random_string
import hcl, tempfile, datetime, tb
from pathlib import Path


from azure.identity import EnvironmentCredential

TEST_AZURE_STORAGE_ACCOUNT = os.getenv("TEST_AZURE_STORAGE_ACCOUNT", None)
TEST_AZURE_STORAGE_CONTAINER = os.getenv("TEST_AZURE_STORAGE_CONTAINER", None)

class TestTbAzureStateStore(unittest.TestCase):

    def setUp(self):
        assert_azurerm_sp_creds()
        self.current_date_slug = datetime.date.today().strftime('%Y-%m-%d')
        self.run_string = get_random_string(10)
        
    def tearDown(self):
        from azure.identity import EnvironmentCredential

        credential = EnvironmentCredential()


        pass        

    def test_rg(self):
        d = tempfile.mkdtemp()
        tfstate_file = "{}/terraform.tfstate".format(d)

        cdir = "azurerm/resource_group"

        retcode = tb.main(["tb", "apply", cdir, '--force', '--allow-no-tfstate-store', '--set-var', "run_id={}".format(self.run_string)])
        assert retcode == 0

        # # assert vpc exists
        # response = self.describe_vpcs()
        
        # count = 0
        # for r in response['Vpcs']:
        #     count += 1

        # assert count == 1

    # def test_tfstate_store(self):
    #     d = tempfile.mkdtemp()
    #     tfstate_file = "{}/terraform.tfstate".format(d)

    #     random_string = get_random_string(64)

    #     with open(tfstate_file, 'w') as fh:
    #         fh.write(random_string)

    #     project = Project(git_filtered=False)
    #     cdir = "azurerm/vnet"
    #     project.set_component_dir(cdir)
    #     project.parse_template()
    #     obj = hcl.loads(project.hclfile)

    #     obj["tfstate_store"] = {
    #         "storage_account" : TEST_AZURE_STORAGE_ACCOUNT,
    #         "bucket_path" : "{}/{}".format(self.current_date_slug, cdir)
    #     }

    #     crs = TfStateStoreAwsS3(args=obj["tfstate_store"], localpath=tfstate_file)

    #     crs.push()
    #     os.unlink(tfstate_file)
    #     crs.fetch()

    #     with open(tfstate_file, 'r') as fh:
    #         content = fh.read()

    #     assert content == random_string

    # def test_encrypted_tfstate_store(self):

    #     d = tempfile.mkdtemp()
    #     tfstate_file = "{}/terraform.tfstate".format(d)
    #     random_string = get_random_string(64)

    #     with open(tfstate_file, 'w') as fh:
    #         fh.write(random_string)

    #     project = Project(git_filtered=False)
    #     cdir = "aws/vpc"
    #     project.set_component_dir(cdir)

    #     crs = TfStateStoreAwsS3(args={}, localpath=tfstate_file)
    
    #     random_passphrase = get_random_string(64)

    #     assert not crs.is_encrypted
    #     crs.set_passphrases([random_passphrase])
    #     assert crs.encrypt()

    #     assert crs.is_encrypted

    #     crs.decrypt()
    #     assert not crs.is_encrypted
    #     with open(tfstate_file, 'r') as fh:
    #         content = fh.read()

    #     assert content == random_string

         
    #     # re encrypt to test decrypt with bad passphrase
    #     assert crs.encrypt()
    #     assert crs.is_encrypted

    #     wrong_passphrase = get_random_string(20)
    #     crs.set_passphrases([wrong_passphrase])

    #     try:
    #         crs.decrypt()
    #         assert False
    #     except WrongPasswordException:
    #         pass

    #     # should still be encrypted post failure
    #     assert crs.is_encrypted
        
    #     with open(tfstate_file, 'r') as fh:
    #         content = fh.read()

    #     assert content != random_string


if __name__ == '__main__':
    unittest.main()
