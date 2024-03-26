#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
import unittest
import cloudicorn, tempfile
from cloudicorn_core import get_random_string, ComponentSourceException, ComponentException

class TestLinkedProject(unittest.TestCase):

    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        #shutil.copytree("mock/mockprojects", self.root_dir, dirs_exist_ok=True)
        #self.d_orig = os.getcwd()
        #os.chdir(self.root_dir)

    def tearDown(self):
        shutil.rmtree(self.root_dir)


    def test_mock_project_b_reads_a1_block_value(self):

        pdira = "mock/mockprojects/a_git_path_tag"
        cdir = "component_a1"

        a_tfstore = get_random_string(10)

        retcode = cloudicorn.main(["cloudicorn", "apply", cdir, '--force', 
                           '--project-dir', pdira,
                           '--set-var', 'source_tag=foo_and_random_string',
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        pdir = "mock/mockprojects/c_git_branch"
        cdir = "component_c2"

        b_tfstore = get_random_string(10)

        retcode = cloudicorn.main(["cloudicorn", "apply", cdir, '--force', 
                           '--project-dir', pdir,
                           '--set-var', 'project_a_path={}'.format(pdira), 
                           '--set-var', 'tfstate_store_path_a={}'.format(os.path.join(self.root_dir, a_tfstore)),
                           '--set-var', 'test_linked_project_branch=test_linked_project',
                           '--set-var', "tfstate_store_path_b={}".format(os.path.join(self.root_dir, b_tfstore))])
        assert retcode == 0


    def test_mock_project_b_reads_a1_block_value_implicit_attr(self):

        pdira = "mock/mockprojects/a_git_path_tag"
        cdir = "component_a1"

        a_tfstore = get_random_string(10)

        retcode = cloudicorn.main(["cloudicorn", "apply", cdir, '--force', 
                           '--project-dir', pdira,
                           '--set-var', 'source_tag=foo_and_random_string',
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        pdir = "mock/mockprojects/c_git_branch"
        cdir = "component_c3"

        b_tfstore = get_random_string(10)

        retcode = cloudicorn.main(["cloudicorn", "apply", cdir, '--force', 
                           '--project-dir', pdir,
                           '--set-var', 'project_a_path={}'.format(pdira), 
                           '--set-var', 'tfstate_store_path_a={}'.format(os.path.join(self.root_dir, a_tfstore)),
                           '--set-var', 'test_linked_project_branch=test_linked_project',
                           '--set-var', "tfstate_store_path_b={}".format(os.path.join(self.root_dir, b_tfstore))])
        assert retcode == 0

if __name__ == '__main__':
    unittest.main()
