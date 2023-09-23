#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys
import unittest
from tbcore import Project, ComponentSourceGit, ComponentSourcePath, ComponentSourceException
import hcl, tempfile


class TestTbComponentSource(unittest.TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_mock_component_source_path(self):

        project = Project(git_filtered=False)
        project.set_component_dir("mock/mocksource/filepath")
        project.parse_template()
        obj = hcl.loads(project.hclfile)
        p = tempfile.mkdtemp()
        cs = ComponentSourcePath(args=obj["source"])
        cs.set_targetdir(p)
        cs.fetch()

        assert os.path.isfile("{}/a.tf".format(p))
        assert os.path.isfile("{}/submodule/b.tf".format(p))

    def test_mock_component_source_gitssh(self):

        project = Project(git_filtered=False)
        project.set_component_dir("mock/mocksource/git")
        project.parse_template()
        obj = hcl.loads(project.hclfile)
        p = tempfile.mkdtemp()
        cs = ComponentSourceGit(args=obj["source"])
        cs.set_targetdir(p)
        cs.fetch()

        assert os.path.isfile("{}/a.tf".format(p))
        assert os.path.isfile("{}/subdir/modules/b.tf".format(p))

    def test_mock_component_source_githttp(self):

        project = Project(git_filtered=False)
        project.set_component_dir("mock/mocksource/githttp")
        project.parse_template()
        obj = hcl.loads(project.hclfile)
        p = tempfile.mkdtemp()
        cs = ComponentSourceGit(args=obj["source"])
        cs.set_targetdir(p)
        cs.fetch()

        assert os.path.isfile("{}/a.tf".format(p))
        assert os.path.isfile("{}/subdir/modules/b.tf".format(p))

    def test_mock_component_source_githttp_fail_branch(self):

        project = Project(git_filtered=False)
        project.set_component_dir("mock/mocksource/githttp")
        project.parse_template()
        obj = hcl.loads(project.hclfile)
        p = tempfile.mkdtemp()
        obj["source"]["branch"] = "fail branch"
        cs = ComponentSourceGit(args=obj["source"])
        cs.set_targetdir(p)

        try:
            cs.fetch()
            assert False
        except ComponentSourceException:
            pass

    def test_mock_component_source_githttp_fail_subdir(self):

        project = Project(git_filtered=False)
        project.set_component_dir("mock/mocksource/githttp")
        project.parse_template()
        obj = hcl.loads(project.hclfile)
        p = tempfile.mkdtemp()
        obj["source"]["path"] = "fail path"
        cs = ComponentSourceGit(args=obj["source"])
        cs.set_targetdir(p)

        try:
            cs.fetch()
            assert False
        except ComponentSourceException:
            pass

if __name__ == '__main__':
    unittest.main()
