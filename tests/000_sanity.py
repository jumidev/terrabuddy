#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import yaml
import cloudicorn, cloudicorn_core
from cloudicorn_core import hcldump, get_random_string
import hcl


class TestSanity(unittest.TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_bad_hclt(self):
        try:
            retcode = cloudicorn.main(["cloudicorn", "parse", "mock/badhclt"])
            assert False
        except cloudicorn_core.HclParseException:
            pass

    def test_good_hclt(self):
        retcode = cloudicorn.main(["cloudicorn", "parse", "mock/goodhclt"])
        assert retcode == 0

    def test_bad_yml(self):
        try:
            retcode = cloudicorn.main(["cloudicorn", "parse", "mock/withvars/badyml"])
            assert False
        except yaml.scanner.ScannerError:
            pass

    def test_no_component(self):
        retcode = cloudicorn.main(["cloudicorn", "parse", "not/a/component"])
        assert retcode == -1

    def test_list_components(self):
        retcode = cloudicorn.main(["cloudicorn", "plan"])
        assert retcode == 100

    def test_missing_remote_state_block(self):
        retcode = cloudicorn.main(["cloudicorn", "plan", "mock/goodhclt", "--key", "COMPONENT_DIRNAME"])
        assert retcode == 110

    def test_parse_missingvars(self):
        retcode = cloudicorn.main(["cloudicorn", "parse", "mock/withvars/missingvars"])
        assert retcode == 120 # not all variables substituted
    
    def test_parse_withvars(self):
        retcode = cloudicorn.main(["cloudicorn", "parse", "mock/withvars/withvars"])
        assert retcode == 0 # all variables substituted

    def test_showvars_withvars(self):
        retcode = cloudicorn.main(["cloudicorn", "showvars", "mock/withvars/withvars"])
        assert retcode == 0 # all variables substituted

    def test_bundle(self):
        retcode = cloudicorn.main(["cloudicorn", "parse", "mock/withvars"])
        assert retcode == 0

    def test_bundle_dry(self):
        retcode = cloudicorn.main(["cloudicorn", "apply", "mock/withvars", "--dry"])
        print(retcode)
        assert retcode == None

    def test_hcldump(self):
        l1 = ["horses", "dogs", 'cats', "mice", "owls"]
        l2 = ["asia", "europe", "northamerica", 'africa', 'australia', "southamerica"]
        l3 = [23,24,65,98,6555]

        # simple list, should fail
        try:
            hcls = hcldump(l1)
            assert False
        except cloudicorn_core.HclDumpException:
            pass

        # dict of strs, should succeed
        o = {}
        for k in l2:
            o[k] = get_random_string(10)

        hcls = hcldump(o)

        o2 = hcl.loads(hcls)
        assert type(o2) == dict

        # dict of ints, should succeed
        o = {}
        i = 0
        for k in l1:
            o[k] = l3[i]
            i+=1

        hcls = hcldump(o)

        o2 = hcl.loads(hcls)
        assert type(o2) == dict

        # dict of list of strs, should succeed
        o = {}
        for k in l1:
            o[k] = []
            for k2 in l2:
                o[k].append(k2)

        hcls = hcldump(o)

        o2 = hcl.loads(hcls)
        assert type(o2) == dict



if __name__ == '__main__':
    unittest.main()
