#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys
import unittest
from tb import Project, ComponentSourceGit, ComponentSourcePath, ComponentSourceException
import hcl, tempfile

path = os.path.dirname(os.path.realpath(__file__))+'/../tb'
pylib = os.path.abspath(path)
sys.path.append(pylib)

class TestTbComponentSource(unittest.TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_vpc_plan(self):
        p = tempfile.mkdtemp()

        project = Project(git_filtered=False)
        project.set_component_dir("aws/vpc")
        project.set_tf_dir(p)
        project.parse_template()
        project.save_outfile()
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
