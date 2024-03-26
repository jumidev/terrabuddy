#!/usr/bin/python3

# -*- coding: utf-8 -*-

import setuptools
from setuptools import setup

with open("../README.md", "r") as fh:
    long_description = fh.read()
    
with open("requirements.txt", "r") as fh:
    install_requires = fh.readlines()

setup(name='cloudicorn-cli',
    version='0.1',
    description='Taking Infrastructure As Code to the next level',
    long_description=long_description,
    long_description_content_type="text/markdown",      
    url='https://github.com/jumidev/cloudicorn-cli',
    author='krezreb',
    author_email='josephbeeson@gmail.com',
    license='MIT',
    packages=["."],
    zip_safe=False,
    install_requires=install_requires,
    entry_points = {
              'console_scripts': [
                  'cloudicorn=cloudicorn:cli_entrypoint',              
                  'cloudicorn_setup=cloudicorn_setup:cli_entrypoint'              
                ]     
          },

    )





