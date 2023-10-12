#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
import unittest
import tb, tempfile
from tbcore import get_random_string, ComponentSourceException


class TestTbLinkedProject(unittest.TestCase):

    def setUp(self):
        self.root_dir = tempfile.mkdtemp()
        #shutil.copytree("mock/mockprojects", self.root_dir, dirs_exist_ok=True)
        #self.d_orig = os.getcwd()
        #os.chdir(self.root_dir)

    def tearDown(self):
        return
        os.chdir(self.d_orig)
        shutil.rmtree(self.root_dir)

    def test_mock_project_b_reads_a1_paths(self):

        pdira = "mock/mockprojects/a"
        cdir = "component_a1"

        a_tfstore = get_random_string(10)

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdira,
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        pdir = "mock/mockprojects/b"
        cdir = "component_b1"

        b_tfstore = get_random_string(10)

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdir,
                           '--set-var', 'project_a_path={}'.format(pdira), 
                           '--set-var', 'tfstate_store_path_a={}'.format(os.path.join(self.root_dir, a_tfstore)), 
                           '--set-var', "tfstate_store_path_b={}".format(os.path.join(self.root_dir, b_tfstore))])
        assert retcode == 0

        #raise Exception(self.root_dir)


    def test_mock_project_b_reads_a1_git(self):

        pdira = "mock/mockprojects/a_git"
        cdir = "component_a1"

        a_tfstore = get_random_string(10)

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdira,
                           '--set-var', "tfstate_store_path_a={}".format(os.path.join(self.root_dir, a_tfstore))])
        assert retcode == 0

        pdir = "mock/mockprojects/c_git"
        cdir = "component_c1"

        b_tfstore = get_random_string(10)

        retcode = tb.main(["tb", "apply", cdir, '--force', 
                           '--project-dir', pdir,
                           '--set-var', 'project_a_path={}'.format(pdira), 
                           '--set-var', 'tfstate_store_path_a={}'.format(os.path.join(self.root_dir, a_tfstore)),
                           '--set-var', 'test_linked_project_branch=test_linked_project',
                           '--set-var', "tfstate_store_path_b={}".format(os.path.join(self.root_dir, b_tfstore))])
        assert retcode == 0

    def test_mock_project_b_reads_a1_git_no_such_branch(self):

        a_tfstore = get_random_string(10)
        pdir = "mock/mockprojects/c_git"
        cdir = "component_c1"

        b_tfstore = get_random_string(10)

        try:
            retcode = tb.main(["tb", "apply", cdir, '--force', 
                            '--project-dir', pdir,
                            '--set-var', 'tfstate_store_path_a={}'.format(os.path.join(self.root_dir, a_tfstore)),
                            '--set-var', 'test_linked_project_branch=BAD_BRANCH',
                            '--set-var', "tfstate_store_path_b={}".format(os.path.join(self.root_dir, b_tfstore))])
            assert False
        except ComponentSourceException:
            pass
        except:
            raise


if __name__ == '__main__':
    unittest.main()
