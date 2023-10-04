#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
from tbcore import assert_azurerm_sp_creds, get_random_string, AzureUtils, TerraformException
import datetime, tb

TEST_AZURE_STORAGE_ACCOUNT = os.getenv("TEST_AZURE_STORAGE_ACCOUNT", None)
TEST_AZURE_STORAGE_CONTAINER = os.getenv("TEST_AZURE_STORAGE_CONTAINER", None)

class TestTbAzureRgVnetStateStore(unittest.TestCase):

    def setUp(self):
        assert_azurerm_sp_creds()
        assert TEST_AZURE_STORAGE_ACCOUNT != None
        assert TEST_AZURE_STORAGE_CONTAINER != None
        self.current_date_slug = datetime.date.today().strftime('%Y-%m-%d')
        self.run_string = get_random_string(10)
        self.run_string2 = get_random_string(10)
        self.azure_utils = AzureUtils()
        self.resource_client =  self.azure_utils.resource_client
        cdir = "azurerm/resource_group_vnet"

        retcode = tb.main(["tb", "apply", cdir, '--force', '--set-var', "run_id={}".format(self.run_string)])
        assert retcode == 0

        cdir = "azurerm/resource_group_vnet"

        retcode = tb.main(["tb", "apply", cdir, '--force', '--set-var', "run_id={}".format(self.run_string2)])
        assert retcode == 0

    def tearDown(self):
        self.resource_client.resource_groups.begin_delete("test_{}".format(self.run_string))
        self.resource_client.resource_groups.begin_delete("test_{}".format(self.run_string2))

    def test_vnet_asg_etc_success(self):
        cdirs = [
            "azurerm/virtual_network",
            "azurerm/asg",
            "azurerm/nsg",
            "azurerm/subnet"
        ]
        for cdir in cdirs: 

            retcode = tb.main(["tb", "apply", cdir, '--force', '--set-var', "run_id={}".format(self.run_string)])
            assert retcode == 0

    def test_vnet_asg_etc_fail_then_success(self):

        cdir = "azurerm/nsg_failapply"
        try:
            retcode = tb.main(["tb", "apply", cdir, '--force', '--set-var', 'fail_rule_priority=300', '--set-var', "run_id={}".format(self.run_string2)])
            assert False
        except TerraformException:
            pass
    
        retcode = tb.main(["tb", "apply", cdir, '--force', '--set-var', 'fail_rule_priority=301', '--set-var', "run_id={}".format(self.run_string2)])
        assert retcode == 0

if __name__ == '__main__':
    unittest.main()
