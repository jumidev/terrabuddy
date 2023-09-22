#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

class MissingCredsException(Exception):
    pass

def assert_aws_creds():
    required = ("AWS_REGION", "AWS_ROLE_ARN", "AWS_ROLE_SESSION_NAME", "AWS_SESSION_TOKEN")
    missing = []
    for c in required:
        val = os.environ.get(c, None)
        if val == None:
            missing.append(c)

    if len(missing) == 0:
        return True

    required = ("AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
    missing = []
    for c in required:
        val = os.environ.get(c, None)
        if val == None:
            missing.append(c)

    for c in required:
        k = "TF_VAR_{}".format(c.lower())
        val = os.environ.get(k, None)
        if val == None:
            missing.append(k)

    if len(missing) > 0:
        raise MissingCredsException("Missing credentials in env vars: {}".format(", ".join(missing)))
    
    return True

def assert_azurerm_creds():
    pass