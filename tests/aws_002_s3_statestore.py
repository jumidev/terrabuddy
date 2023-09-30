#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, shutil
import unittest
from tbcore import Project, TfStateStoreAwsS3, WrongPasswordException
from tbcore import assert_aws_creds, get_random_string
import hcl, tempfile, datetime
from pathlib import Path
import random
import string


TEST_S3_BUCKET = os.getenv("TEST_S3_BUCKET", None)

class TestTbAwsS3StateStore(unittest.TestCase):

    def setUp(self):
        assert_aws_creds()
        assert TEST_S3_BUCKET != None
        self.current_date_slug = datetime.date.today().strftime('%Y-%m-%d')
        
    def tearDown(self):
        pass        

    def test_aws_s3_tfstate_store(self):
        d = tempfile.mkdtemp()
        tfstate_file = "{}/terraform.tfstate".format(d)

        random_string = get_random_string(64)

        with open(tfstate_file, 'w') as fh:
            fh.write(random_string)

        project = Project(git_filtered=False)
        cdir = "aws/vpc"
        project.set_component_dir(cdir)
        project.parse_template()
        obj = hcl.loads(project.hclfile)

        obj["tfstate_store"] = {
            "bucket" : TEST_S3_BUCKET,
            "bucket_path" : "{}/{}".format(self.current_date_slug, cdir)
        }

        crs = TfStateStoreAwsS3(args=obj["tfstate_store"], localpath=tfstate_file)

        crs.push()
        os.unlink(tfstate_file)
        crs.fetch()

        with open(tfstate_file, 'r') as fh:
            content = fh.read()

        assert content == random_string

    def test_encrypted_tfstate_store(self):

        d = tempfile.mkdtemp()
        tfstate_file = "{}/terraform.tfstate".format(d)
        random_string = get_random_string(64)

        with open(tfstate_file, 'w') as fh:
            fh.write(random_string)

        project = Project(git_filtered=False)
        cdir = "aws/vpc"
        project.set_component_dir(cdir)

        crs = TfStateStoreAwsS3(args={}, localpath=tfstate_file)
    
        random_passphrase = get_random_string(64)

        assert not crs.is_encrypted
        crs.set_passphrases([random_passphrase])
        assert crs.encrypt()

        assert crs.is_encrypted

        crs.decrypt()
        assert not crs.is_encrypted
        with open(tfstate_file, 'r') as fh:
            content = fh.read()

        assert content == random_string

         
        # re encrypt to test decrypt with bad passphrase
        assert crs.encrypt()
        assert crs.is_encrypted

        wrong_passphrase = get_random_string(20)
        crs.set_passphrases([wrong_passphrase])

        try:
            crs.decrypt()
            assert False
        except WrongPasswordException:
            pass

        # should still be encrypted post failure
        assert crs.is_encrypted
        
        with open(tfstate_file, 'r') as fh:
            content = fh.read()

        assert content != random_string


if __name__ == '__main__':
    unittest.main()
