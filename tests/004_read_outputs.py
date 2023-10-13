#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
import unittest
import tb, tempfile
from tbcore import get_random_string, ComponentSourceException, ComponentException, Project

class TestTbLinkedProject(unittest.TestCase):

    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        #shutil.copytree("mock/mockprojects", self.root_dir, dirs_exist_ok=True)
        #self.d_orig = os.getcwd()
        #os.chdir(self.root_dir)

    def tearDown(self):
        shutil.rmtree(self.root_dir)

    def test_mock_project_a_reads_foo(self):

        pdira = "mock/mockprojects/a"
        cdir = "component_a1"

        a_tfstore = get_random_string(10)

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdira,
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        retcode = tb.main(["tb", "refresh", cdir,  
                           '--project-dir', pdira,
                           '--key', 'foo',
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        project = Project(git_filtered=False,  wdir=pdira, project_vars={
            "tfstate_store_path_a" : os.path.join(self.root_dir, a_tfstore)
        })
        project.set_component_dir(cdir)
        project.setup_component_tfstore()
        assert project.component.get_output("foo") == "bar"

        assert "random_string" in project.component.get_output_keys()


if __name__ == '__main__':
    unittest.main()
