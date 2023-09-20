#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, sys
import unittest
import logging
import yaml

path = os.path.dirname(os.path.realpath(__file__))+'/../tb'
pylib = os.path.abspath(path)
sys.path.append(pylib)

import tb

class TestTbSanity(unittest.TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_bad_hclt(self):
        try:
            retcode = tb.main(["tb", "parse", "mock/badhclt"])
            assert False
        except tb.HclParseException:
            pass

    def test_good_hclt(self):
        retcode = tb.main(["tb", "parse", "mock/goodhclt"])
        assert retcode == 0

    def test_bad_yml(self):
        try:
            retcode = tb.main(["tb", "parse", "mock/withvars/badyml"])
            assert False
        except yaml.scanner.ScannerError:
            pass

    def test_no_component(self):
        retcode = tb.main(["tb", "parse", "not/a/component"])
        assert retcode == -1

    def test_list_components(self):
        retcode = tb.main(["tb", "plan"])
        assert retcode == 100

    # def test_missing_remote_state_block(self):
    #     retcode = tb.main(["tb", "plan", "mock/goodhclt", "--key", "COMPONENT_DIRNAME"])
    #     assert retcode == 110

    def test_parse_missingvars(self):
        retcode = tb.main(["tb", "parse", "mock/withvars/missingvars"])
        assert retcode == 120 # not all variables substituted
    
    def test_parse_withvars(self):
        retcode = tb.main(["tb", "parse", "mock/withvars/withvars"])
        assert retcode == 0 # all variables substituted

    def test_showvars_withvars(self):
        retcode = tb.main(["tb", "showvars", "mock/withvars/withvars"])
        assert retcode == 0 # all variables substituted

    def test_bundle(self):
        retcode = tb.main(["tb", "parse", "mock/withvars"])
        assert retcode == 0

    def test_bundle_dry(self):
        retcode = tb.main(["tb", "apply", "mock/withvars", "--dry"])
        print(retcode)
        assert retcode == None


if __name__ == '__main__':
    unittest.main()
