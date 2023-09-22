#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, shutil
import unittest
from tb import Project, ComponentRemoteStateAwsS3, WrongPasswordException
import hcl, tempfile, datetime
from pathlib import Path
import random
import string

path = os.path.dirname(os.path.realpath(__file__))+'/../tb'
pylib = os.path.abspath(path)
sys.path.append(pylib)

TEST_S3_BUCKET = os.getenv("TEST_S3_BUCKET", None)

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return str(result_str)


class TestTbAwsS3RemoteState(unittest.TestCase):

    def setUp(self):
        assert TEST_S3_BUCKET != None
        self.current_date_slug = datetime.date.today().strftime('%Y-%m-%d')


        
    def tearDown(self):
        pass        

    def test_aws_s3_remote_state(self):
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

        obj["remote_state"] = {
            "bucket" : TEST_S3_BUCKET,
            "bucket_path" : "{}/{}".format(self.current_date_slug, cdir)
        }

        crs = ComponentRemoteStateAwsS3(args=obj["remote_state"], localpath=tfstate_file)

        crs.push()
        os.unlink(tfstate_file)
        crs.fetch()

        with open(tfstate_file, 'r') as fh:
            content = fh.read()

        assert content == random_string

    def test_encrypted_remote_state(self):

        d = tempfile.mkdtemp()
        tfstate_file = "{}/terraform.tfstate".format(d)
        random_string = get_random_string(64)

        with open(tfstate_file, 'w') as fh:
            fh.write(random_string)

        project = Project(git_filtered=False)
        cdir = "aws/vpc"
        project.set_component_dir(cdir)

        crs = ComponentRemoteStateAwsS3(args={}, localpath=tfstate_file)
    
        random_passphrase = get_random_string(64)

        assert not crs.is_encrypted
        crs.set_passphrase(random_passphrase)
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
        crs.set_passphrase(wrong_passphrase)

        try:
            crs.decrypt()
            assert False
        except WrongPasswordException:
            pass

        # shoud still be encrypted post failure
        assert crs.is_encrypted
        
        with open(tfstate_file, 'r') as fh:
            content = fh.read()

        assert content != random_string


if __name__ == '__main__':
    unittest.main()
