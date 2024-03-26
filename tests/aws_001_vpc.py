#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys
import unittest
from cloudicorn_core import Project, ComponentSourceGit
import hcl, tempfile

class TestAwsVpc(unittest.TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_vpc_fetch_source(self):
        p = tempfile.mkdtemp()

        project = Project(git_filtered=False)
        project.set_component_dir("aws/vpc")
        project.set_tf_dir(p)
        project.save_parsed_component()
        assert os.path.isfile("{}/component.hcl".format(p))

        obj = hcl.loads(project.hclfile)
        cs = ComponentSourceGit(args=obj["source"])
        cs.set_targetdir(p)
        cs.fetch()

        assert os.path.isfile("{}/main.tf".format(p))
        assert os.path.isfile("{}/backend.tf".format(p))
        assert os.path.isfile("{}/variables.tf".format(p))



if __name__ == '__main__':
    unittest.main()
