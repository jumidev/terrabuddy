#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, hcl, tempfile, json
import unittest
import tb
from tb import Project, TfStateStoreAwsS3
import assert_creds
import random
import string

import boto3
from botocore.exceptions import ClientError
import botocore


TEST_S3_BUCKET = os.getenv("TEST_S3_BUCKET", None)

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return str(result_str)

class TestTbAwsPlanVpc(unittest.TestCase):

    def setUp(self):
        self.boto_client = boto3.client('ec2')
        assert TEST_S3_BUCKET != None

        self.run_string = get_random_string(10)
        assert_creds.assert_aws_creds()

    def tearDown(self):
        response = self.describe_vpcs()
        
        for r in response['Vpcs']:
            VpcId = r['VpcId']

            response = self.boto_client.delete_vpc(
                VpcId=VpcId,
            )        

    def test_plan(self):
        retcode = tb.main(["tb", "plan", "aws/vpc", "--allow-no-tfstate-store"])
        assert retcode == 0

    def describe_vpcs(self):
        return self.boto_client.describe_vpcs(Filters=[{'Name':'tag:Name','Values':["example vpc {}".format(self.run_string)]}])
    
    def test_apply_delete(self):
        d = tempfile.mkdtemp()
        tfstate_file = "{}/terraform.tfstate".format(d)

        cdir = "aws/vpc_tfstate"

        os.environ["run_id"] = self.run_string
        retcode = tb.main(["tb", "apply", cdir, '--force'])
        assert retcode == 0

        # assert vpc exists
        response = self.describe_vpcs()
        
        count = 0
        for r in response['Vpcs']:
            count += 1

        assert count == 1

        # check that remote state is present on s3
        project = Project(git_filtered=False)
        project.set_component_dir(cdir)
        project.parse_template()
        obj = hcl.loads(project.hclfile)

        crs = TfStateStoreAwsS3(args=obj["tfstate_store"], localpath=tfstate_file)

        crs.fetch()

        with open(tfstate_file, 'r') as fh:
            rs = json.load(fh)

        assert rs["outputs"]["name"]["value"] == "example vpc {}".format(self.run_string)

        # now destroy
        retcode = tb.main(["tb", "destroy", cdir, '--force'])
        assert retcode == 0

        # assert vpc gone
        response = self.describe_vpcs()
        
        count = 0
        for r in response['Vpcs']:
            count += 1

        assert count == 0


if __name__ == '__main__':
    unittest.main()
