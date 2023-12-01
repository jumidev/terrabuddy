#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
import unittest
import tb, tempfile
from tbcore import get_random_string, ComponentSourceException, ComponentException

class TestTbLinkedProject(unittest.TestCase):

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

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdira,
                           '--set-var', 'source_tag=foo_and_random_string',
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        pdir = "mock/mockprojects/c_git_branch"
        cdir = "component_c2"

        b_tfstore = get_random_string(10)

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdir,
                           '--set-var', 'project_a_path={}'.format(pdira), 
                           '--set-var', 'tfstate_store_path_a={}'.format(os.path.join(self.root_dir, a_tfstore)),
                           '--set-var', 'test_linked_project_branch=test_linked_project',
                           '--set-var', "tfstate_store_path_b={}".format(os.path.join(self.root_dir, b_tfstore))])
        assert retcode == 0


if __name__ == '__main__':
    unittest.main()
