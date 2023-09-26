#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys,  yaml, os

from tbcore import log, debug, Utils, assert_aws_creds, assert_azurerm_creds, MissingCredsException
from tbcore import dir_is_git_repo, git_rootdir
from git import Repo
from pathlib import Path
import re, tempfile
import time, shutil
import argparse

PACKAGE = "tb_setup"
LOG = True
DEBUG=False

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.shortcuts import button_dialog
from prompt_toolkit.shortcuts import input_dialog
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit.shortcuts import yes_no_dialog


class NewProject():

    def __init__(self) -> None:
        self.name = None
        self.saved = False
        self.root_dir = None
        self.git_clone = None
        self.envs = []

    def checkstr(self, s):
        regex = r"^[a-zA-Z0-9_-]*$"
        matches = re.search(regex, s)
        return matches != None

    def tui(self):
        # ask for project dir
        # if dir is already project, fail
        # ask for project name
        # ask to git init
        # ask for envs
        # ask to save
        # save

        dir = None
        while dir == None:
            d = input_dialog(
            title='Project Directory',
            text='Directory to save project to (leave blank for current working dir):').run()
        
            if d == "":
                dir = os.getcwd()
            elif not self.checkstr(d):
                ok = message_dialog(
                    title='Error',
                    text='Project directory can only contain alphanumeric characters, numbers, underscores and hyphens.').run()
                time.sleep(0.3)
            else:
                dir = d
                
        self.root_dir = dir

        if self.project_already_setup:
            ok = message_dialog(
            title='Error',
            text='Project {} is already setup as a project, please provide an empty directory or freshly cloned git repo.'.format(dir)).run()
            return

        name = None
        n = os.path.basename(self.root_dir)
        while name == None:
            n = input_dialog(
            title='Project name',
            default=n,
            text='Project name:').run()
        
            if not self.checkstr(n):
                ok = message_dialog(
                    title='Error',
                    text='Project name can only contain alphanumeric characters, numbers, underscores and hyphens.').run()
                time.sleep(0.3)
            else:
                name = n

        self.name = name

        if not self.is_git:
            result = radiolist_dialog(
                values=[
                    ("clone", "Clone an existing repo"),
                    ("init", "Init a fresh repo"),
                    ("skip", "Skip this step")
                ],
                title="Setup git?",
                text="Usually projects are version controlled using git"
            ).run()

            if result == "clone":
                r = ""
                repo = None
                t = tempfile.mkdtemp()

                while repo == None:
                    r = input_dialog(
                    title='Git repo',
                    default=r,
                    text='Repo url:').run()
                
                    try:
                        Repo.clone_from(r, t, depth=1)
                        repo = r
                    except Exception as e:
                        ok = message_dialog(
                            title='Error',
                            text='Error cloning repo: {}.'.format(str(e))).run()
                        time.sleep(0.3)
                    shutil.rmtree(t)

                self.git_clone = repo
            elif result == "init":
                self.git_clone = "init"


        result = yes_no_dialog(
            title='Setup root-level environment dirs',
            text='Do you want to specify root level projects dirs to be environment dirs?').run()
                
        print(result)
        if result:
            e = None
            s = "dev,staging,preprod,prod"
            while e == None:
                s = input_dialog(
                title='Environments',
                default=s,
                text='Comma-separated environments:').run()
            
                envs = s.split(",")
                for env in envs:
                    if not self.checkstr(env.strip()):
                        ok = message_dialog(
                            title='Error',
                            text='environments can only contain alphanumeric characters, numbers, underscores and hyphens.').run()
                        time.sleep(0.3)
                        e = None
                        break
                    else:
                        e = s

            self.envs = envs

        
        txt = ["Project '{}' will be saved in {}".format(self.name, self.root_dir)]
        if self.git_clone == "init":
            txt.append("✓ will be initialized as a new git repo")
        elif self.git_clone != None:
            txt.append("✓ will be cloned from {}".format(self.git_clone))

        if self.envs != None:
            txt.append("✓ {} root level environments will be created: {}".format(len(self.envs), ", ".join(self.envs)))

        result = yes_no_dialog(
            title='Ready to save',
            text="\n".join(txt)
            ).run()

        if result:
            self.save()
            return True
        
        return False


    @property
    def yml_file(self):
        return "{}/project.yml".format(self.root_dir)

    @property
    def gitignore_file(self):
        return "{}/.gitignore".format(self.root_dir)
        
    @property
    def is_git(self):
        if not os.path.isdir(self.root_dir):
            return False
        r = git_rootdir(self.root_dir)
        return r != None

    @property
    def project_already_setup(self):
        if not os.path.isdir(self.root_dir):
            return False
        
        if os.path.isfile(self.yml_file):
            return True
          
        return False

    def read_project(self):
        if self.project_already_setup:
            with open(self.yml_file, 'r') as fh:
                d = yaml.load(fh, Loader=yaml.FullLoader)

            return d
        
        return None

    def save(self):
        if not os.path.isdir(self.root_dir):
            os.makedirs(self.root_dir)

        if self.git_clone == "init":
            Repo.init(self.root_dir)
        elif self.git_clone != None:
            Repo.clone_from(self.git_clone, self.root_dir)

        with open(self.yml_file, 'w') as fh:
            yaml.dump({
                "project_name" : self.name
            }, fh)

        gitignore = []
        Path(self.gitignore_file).touch()

        with open(self.gitignore_file, 'r') as fh:
            gitignore = fh.readlines()

        want = [".envrc"]
        for w in want:
            if w not in gitignore:
                gitignore.append(w)

        with open(self.gitignore_file, 'w') as fh:
            fh.write("\n".join(gitignore))

        for e in self.envs:
            e = e.strip()
            d = "{}/{}".format(self.root_dir, e)

            if not os.path.isdir(d):
                os.makedirs(d)

            with open("{}/env.yml".format(d), "w") as fh:
                yaml.dump({"env": e}, fh)
                 

def main(argv=[]):

    parser = argparse.ArgumentParser(description='',
    add_help=True,
    formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--debug', action='store_true', help='display debug messages')
    args = parser.parse_args(args=argv)

    if args.debug or os.getenv('TB_DEBUG', 'n')[0].lower() in ['y', 't', '1'] :
        global DEBUG
        DEBUG = True
        log("debug mode enabled")

    menu = {
        "main":  {
            "title" : "{} Main Menu".format(PACKAGE),
            "text"  : "Select from the following options",
            "items" : [
                ("new_project", "New project"),
                ("goto:creds_setup", "Setup cloud credentials"),
                ("goto:tfstore_setup", "Setup tfstate storage"),
                ("goto:terraform", "Install/upgrade terraform"),
                ("goto:extras", "Install extras"),
                ("quit", "Exit"),

            ]
        }, "extras": {
            "title" : "Install extras",
            "text"  : "Select from the following options",
            "items" : [
                ("awscli", "install AWS cli"),
                ("azurecli", "install Azure cli"),
                ("direnv", "install direnv"),
                ("pika", "install pika"),
                ("goto:main", "Back"),
            ]            
        }
        
        
    }
    
    # parser = argparse.ArgumentParser(description='tb_setup set up new projects',
    # add_help=True,
    # formatter_class=argparse.RawTextHelpFormatter) 

    # parser.add_argument('command', default=None, nargs='*', help='command to run ({})'.format(", ".join(commands)))
    # parser.add_argument('--debug', action='store_true', help='display debug messages')

    # args = parser.parse_args(args=argv)

    # if args.debug or os.getenv('TB_DEBUG', 'n')[0].lower() in ['y', 't', '1'] :
    #     global DEBUG
    #     DEBUG = True
    #     log("debug mode enabled")

    proj = NewProject()

    if proj.tui():
    # result = radiolist_dialog(
    #     values=menu["main"]["items"],
    #     title=menu["main"]["title"],
    #     text=menu["main"]["text"]
    # ).run()

        return 0

def cli_entrypoint():
    retcode = main(sys.argv[1:])
    exit(retcode)

if __name__ == '__main__':
    retcode = main(sys.argv)
    exit(retcode)
