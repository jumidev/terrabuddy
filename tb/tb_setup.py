#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys,  yaml, os

from tbcore import log, Utils, assert_aws_creds, assert_azurerm_sp_creds, azurerm_sp_cred_keys, aws_cred_keys, aws_test_creds
from tbcore import git_rootdir, run, HclParseException
from git import Repo
from pathlib import Path
import re, tempfile
import time, shutil
import argparse
import hcl

import boto3

PACKAGE = "tb_setup"
LOG = True
DEBUG=False

from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.shortcuts import input_dialog
from prompt_toolkit.shortcuts import message_dialog
from prompt_toolkit.shortcuts import yes_no_dialog, button_dialog


class NewProject():

    def __init__(self) -> None:
        self.name = None
        self.saved = False
        self.git_clone = None
        self.make_readme = None
        self.envs = []

        # can be over ridden for testing purposes
        self.dir = os.path.abspath(os.getcwd())


    def checkstr(self, s):
        regex = r"^[a-zA-Z0-9_-]*$"
        matches = re.search(regex, s)
        return matches != None

    def confirm_leave(self):
        return yes_no_dialog(
            title='Confirm',
            text='You sure you want to quit new project setup?.').run()

    def tui(self):
        # if dir is already project, fail
        # ask for project name
        # ask to git init
        # ask for envs
        # ask for readme.md
        # ask to save
        # save

        if self.project_already_setup:
            ok = message_dialog(
            title='Error',
            text='Directory is already setup as a project.').run()
            return

        name = None
        n = os.path.basename(os.path.abspath(os.getcwd()))
        while name == None:
            n = input_dialog(
            title='Project name',
            default=n,
            text='Project name:').run()
        
            if n == None:
                if self.confirm_leave():
                    return
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
            if result == None:
                if self.confirm_leave():
                    return
            if result == "clone":
                r = ""
                repo = None
                t = tempfile.mkdtemp()

                while repo == None:
                    r = input_dialog(
                    title='Git repo',
                    default=r,
                    text='Repo url:').run()
                
                    if r == None:
                        if self.confirm_leave():
                            return
                    try:
                        Repo.clone_from(r, t, depth=1)
                        repo = r
                        if os.path.isfile("{}/README.md".format(t)):
                            self.make_readme = False
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

        if os.path.isfile("{}/README.md".format(self.root_dir)):
            self.make_readme = False

        if self.make_readme == None:
            result = yes_no_dialog(
                title='Setup README.md?',
                text='Do you want to add a boilerplate README.md file?').run()
                    
            self.make_readme = result

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
    def root_dir(self):
        return self.dir

    @property
    def yml_file(self):
        return "{}/project.yml".format(self.root_dir)

    @property
    def gitignore_file(self):
        return "{}/.gitignore".format(self.root_dir)
        
    @property
    def is_git(self):
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

        md = []
        md.append("# Project {}".format(self.name))
        md.append("")

        if len(self.envs) > 0:
            md.append("Environments:")
            for e in self.envs:
                e = e.strip()
                md.append("- {}".format(e))
                d = "{}/{}".format(self.root_dir, e)

                if not os.path.isdir(d):
                    os.makedirs(d)

                with open("{}/env.yml".format(d), "w") as fh:
                    yaml.dump({"env": e}, fh)
            md.append("")


        if self.make_readme:
            with open("{}/README.md".format(self.root_dir), "w") as fh:
                fh.write("\n".join(md))

class SetupTfStateStorage(NewProject):
    
    @property
    def tfstate_file(self):
        return "{}/tfstate_store.hclt".format(self.root_dir)
    
    def aws_bucket_exists(self, bucket):
        s3 = boto3.client("s3")

        try:
            s3.head_bucket(Bucket=bucket)
            return True
        except:
            return False
        
    def load(self):
        if not os.path.isfile(self.tfstate_file):
            return 
        
        with open(self.tfstate_file, 'r') as fp:
            try:
                obj = hcl.load(fp)
                return obj
            except:
                raise HclParseException("FATAL: An error occurred while parsing {}\nPlease verify that this file is valid hcl syntax".format(path))


    def existing_tfstate_store_setup(self):
        try:
            o = self.load()
            if "tfstate_store" not in o:
                return (False, False)
        except:
            return (False, False)
        
        tfstate_store = o["tfstate_store"]
        if "bucket" in tfstate_store:
            return ("aws", tfstate_store.items())
        elif "storage_account" in tfstate_store:
            return ("azure", tfstate_store.items())
        elif "path" in tfstate_store:
            return ("path", tfstate_store.items())
        
        return False


    def tui(self):
        # if dir is already project, fail
        # ask for project name
        # ask to git init
        # ask for envs
        # ask for readme.md
        # ask to save
        # save

        if not self.project_already_setup:
            ok = message_dialog(
            title='Error',
            text='Directory is not setup as a project, please make a New project first.').run()
            return

        (existing, items) = self.existing_tfstate_store_setup()
        if existing != False:
            i = ["\n"]
            for k,v in items:
                i.append("{} = {}".format(k,v))
            i.append("\n")
            ans = yes_no_dialog(
            title='Hmm....',
            text='tfstate_store currently configured for {}.\n{}\nReconfigure from scratch?'.format(existing, "\n".join(i))).run()
            
            if not ans:
                return
            
        # aws creds
        aws = False
        try:
            aws = assert_aws_creds()
        except:
            pass

        # azure creds
        azure = False
        try:
            azure = assert_azurerm_sp_creds()
        except:
            pass

        if aws:
            ans = yes_no_dialog(
            title='AWS creds',
            text='Setup AWS S3 bucket tfstore_storage?').run()
            
            if ans:
                bucket = ""
                while bucket == "":
                    bucket = input_dialog(
                    title="Bucket",
                    default=bucket,
                    text='Please specify a bucket in region {}'.format(os.getenv("AWS_REGION"))).run()

                    if bucket == None:
                        return
                    
                    if not self.aws_bucket_exists(bucket):
                        ans = yes_no_dialog(
                        title='Hmm....',
                        text='It looks like bucket {} does not exist (or your credentials do not allow you access to it).\nProceed anyway?'.format(bucket)).run()

                        if not ans:
                            bucket == ""
                            time.sleep(0.3)


                bucket_path = "tfstate"

                existing_project = self.read_project()
                if existing_project != None:
                    if "project_name" in existing_project:
                        bucket_path = "tfstate/"+existing_project["project_name"]+'/${COMPONENT_PATH}'

                bucket_path = input_dialog(
                title="Bucket path",
                default=bucket_path,
                text='Please specify a path prefix for storing tfstore files').run()

                ans = yes_no_dialog(
                title='Save',
                text='Save to tfstate_store.hclt?').run()

                if ans:
                    h = {
                        "tfstate_store" : {
                            "bucket" : bucket,
                            "bucket_path" : bucket_path
                        }
                    }
                    Path(self.tfstate_file).touch()
                    with open(self.tfstate_file, 'w') as fh:
                        fh.write("tfstate_store {\n")
                        fh.write("     bucket      = \"{}\" \n".format(bucket))
                        fh.write("     bucket_path = \"{}\" \n".format(bucket_path))
                        fh.write("}\n")
                        

        elif azure:
            pass


class SetupCreds():

    @property
    def menu(self):
        return {
            "title" : "Setup cloud credentials",
            "text"  : "Select from the following cloud providers",
            "items" : [
                ("aws", "AWS"),
                ("azure", "Azure"),
                ("gcp", "GCP"),
                (None, "Done")

            ]
        }

    def tui(self):
        direnv = False
        (out, err, exitcode) = run("which direnv")
        if exitcode == 0:
            direnv = True

        creds = []

        # aws creds
        aws = False
        try:
            aws = assert_aws_creds()
        except:
            pass

        # azure creds
        azure = False
        try:
            azure = assert_azurerm_sp_creds()
        except:
            pass

        if aws:
            creds.append("aws")
        if azure:
            creds.append("azure")
        
        if len(creds) > 0:
            ans = button_dialog(
            title='Hmm....',
            buttons=[("Leave as-is", False), ("Reconfigure", True)],
            text='Credentials already configured for {}.\nReconfigure credentials?'.format(" and ".join(creds))).run()
            
            if not ans:
                return
            

        result = "aws"
        while result != None:
            result = radiolist_dialog(
                values=self.menu["items"],
                title=self.menu["title"],
                text=self.menu["text"],
                default = result
            ).run()

            creds = {}

            if result == "aws":
                for k in aws_cred_keys():
                    v = input_dialog(
                    title=k,
                    default=os.getenv(k, ""),
                    text='Please input {}:'.format(k)).run()

                    creds[k] = v
                    os.environ[k] = v

                ans = yes_no_dialog(
                title='Test',
                text='Test credentials?').run()

                if ans:
                    if not aws_test_creds():
                        ans = yes_no_dialog(
                        title='FAIL',
                        text='Credentials rejected, start over?').run()
                        if ans:
                            continue
                        return
                    


            if result == "azure":
                for k in azurerm_sp_cred_keys():
                    v = input_dialog(
                    title=k,
                    default=os.getenv(k, ""),
                    text='Please input {}:\n\nSee https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/guides/service_principal_client_secret for details'.format(k)).run()

                    creds[k] = v

            if len(creds.keys()) > 0:
                ans = yes_no_dialog(
                title='Save'.format(result),
                text='Save credentials to {}/.envrc?'.format(os.path.abspath(os.getcwd()))).run()

                if ans:
                    Path(".envrc").touch()

                    envrc = []
                    with open(".envrc", 'r') as fh:
                        for line in fh.readlines():
                            ok = True
                            for k in creds.keys():
                                if line.strip().startswith("export {}".format(k)):
                                    ok = False

                            if ok:
                                envrc.append(line)

                    with open(".envrc", 'w') as fh:
                        for l in envrc:
                            fh.writelines(l)
                        for k,v in creds.items():
                            fh.write("\nexport {}=\"{}\"".format(k,v))
                        fh.write("\n")

                    if not direnv:
                        ok = message_dialog(
                        title='Oops...',
                        text='direnv is not installed.  Check out https://direnv.net/docs/installation.html').run()

def main(argv=[]):

    proj = NewProject()


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
            "text"  : "Current working directory is {}\nSelect from the following options".format(os.path.abspath(os.getcwd())),
            "items" : [
                ("terraform", "Install/upgrade terraform"),
                (None, "Exit")

            ]
        }
        
        
    }
    


    result = "new_project"
    if proj.project_already_setup:
        result = "creds"

    while result != None:
        menuvalues = list(menu["main"]["items"])

        if proj.project_already_setup:
            menuvalues.insert(0,("tfstore_setup", "Setup/check tfstate storage"))
            menuvalues.insert(0,("creds", "Setup/check cloud credentials"))
        else:
            menuvalues.insert(0,('new_project', 'New Project'))


        result = radiolist_dialog(
            values=menuvalues,
            title=menu["main"]["title"],
            text=menu["main"]["text"],
            default = result
        ).run()

        u = Utils()

        if result == 'new_project':

            proj.tui()

        if result == "terraform":
            try:
                missing, outdated = u.check_setup()
                u.terraform_currentversion()
                if result in missing:
                    u.install_terraform()
                    ok = message_dialog(
                    title='Success',
                    text='terraform {} successfully installed.'.format(u.terraform_currentversion()[0])).run()
                    continue
                if result in outdated:
                    ans = yes_no_dialog(
                    title='{} is out of date'.format(result),
                    text='upgrade to latest version?').run()
                    if ans:
                        u.install_terraform()
                else:
                    ok = message_dialog(
                    title='Nothing to do',
                    text='terraform {} is already installed in {} and is the latest version.'.format(u.terraform_currentversion()[0], u.terraform_path)).run()
            except Exception as e:
                ok = message_dialog(
                title='Error',
                text='Could not check {}\n {}.'.format(result, str(e))).run()

        if result == "creds":
            c = SetupCreds()
            c.tui()

        if result == "tfstore_setup":
            tfproj = SetupTfStateStorage()
            tfproj.tui()

                

def cli_entrypoint():
    retcode = main(sys.argv[1:])
    exit(retcode)

if __name__ == '__main__':
    retcode = main(sys.argv)
    exit(retcode)
