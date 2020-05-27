#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, sys, stat
import unittest
import logging
import tempfile

path = os.path.dirname(os.path.realpath(__file__))+'/../tb'
pylib = os.path.abspath(path)
sys.path.append(pylib)

import tb

class TestTbSetup(unittest.TestCase):

    def setUp(self):
        self.u = tb.Utils()

        version, url = self.u.terragrunt_currentversion()

        t = tempfile.NamedTemporaryFile(delete=False)
        self.terragrunt_mock_path = t.name

        t.write(bytes("""#!/usr/bin/env bash
        echo "terragrunt version {}"
        """.format(version), 'utf-8'))
        t.close()
        os.chmod(self.terragrunt_mock_path, stat.S_IRWXU)
        
    def tearDown(self):
        os.unlink(self.terragrunt_mock_path)

    def test_setup_current(self):

        print(self.terragrunt_mock_path)
        os.environ["TERRAGRUNT_BIN"] = self.terragrunt_mock_path
        os.environ["TERRAFORM_BIN"] = os.path.dirname(os.path.realpath(__file__))+'/bin/mock_terraform_current'
        retcode = tb.main(["tb", "--check-setup"])
        assert retcode == 0

    def test_check_setup_outdated(self):
        u = tb.Utils(
            terragrunt_path = os.path.dirname(os.path.realpath(__file__))+'/bin/mock_terragrunt_outdated',
            terraform_path = os.path.dirname(os.path.realpath(__file__))+'/bin/mock_terraform_outdated'
        )

        missing, outdated = u.check_setup(verbose=True)

        assert len(missing) == 0
        assert "terraform" in outdated
        assert "terragrunt" in outdated

    def test_check_setup_missing(self):
        u = tb.Utils(
            terragrunt_path = os.path.dirname(os.path.realpath(__file__))+'/bin/none',
            terraform_path = os.path.dirname(os.path.realpath(__file__))+'/bin/none'
        )

        missing, outdated = u.check_setup(verbose=True)

        print (missing)
        print (outdated)
        assert len(outdated) == 0
        assert "terraform" in missing
        assert "terragrunt" in missing

if __name__ == '__main__':
    unittest.main()
