#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
import tb

class TestTbSetup(unittest.TestCase):

    def test_setup_current(self):

        os.environ["TERRAFORM_BIN"] = os.path.dirname(os.path.realpath(__file__))+'/bin/mock_terraform_current'
        retcode = tb.main(["tb", "--check-setup"])
        assert retcode == 0

    def test_check_setup_outdated(self):
        u = tb.Utils(
            terraform_path = os.path.dirname(os.path.realpath(__file__))+'/bin/mock_terraform_outdated'
        )

        missing, outdated = u.check_setup(verbose=True)

        assert len(missing) == 0
        assert "terraform" in outdated

    def test_check_setup_missing(self):
        u = tb.Utils(
            terraform_path = os.path.dirname(os.path.realpath(__file__))+'/bin/none'
        )

        missing, outdated = u.check_setup(verbose=True)

        print (missing)
        print (outdated)
        assert len(outdated) == 0
        assert "terraform" in missing

if __name__ == '__main__':
    unittest.main()
