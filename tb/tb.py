#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, sys, yaml, hcl, zipfile, shutil, time
from fuzzywuzzy import fuzz
import argparse, glob, tempfile
from subprocess import Popen, PIPE
from pyfiglet import Figlet
import requests
import datetime
from collections import OrderedDict
import re, hashlib
from pathlib import Path

from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from git import Repo, Remote, InvalidGitRepositoryError
import time

import boto3
from botocore.exceptions import ClientError

PACKAGE = "tb"
LOG = True
DEBUG=False

def anyof(needles, haystack):
    for n in needles:
        if n in haystack:
            return True

    return False

def stylelog(s):
    if type(s) is str:
        s = s.replace("<b>", "\033[1m")
        s = s.replace("<u>", "\033[4m")
        s = s.replace("</u>", "\033[0;0m")
        s = s.replace("</b>", "\033[0;0m")
    return s

def log(s):
    if LOG == True:
        print (stylelog(s))

def debug(s):
    if DEBUG == True:
        print (stylelog(s))

def run(cmd, splitlines=False, env=os.environ, raise_exception_on_fail=False, cwd='.'):
    # you had better escape cmd cause it's goin to the shell as is
    proc = Popen([cmd], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True, env=env, cwd=cwd)
    out, err = proc.communicate()
    if splitlines:
        out_split = []
        for line in out.split("\n"):
            line = line.strip()
            if line != '':
                out_split.append(line)
        out = out_split

    exitcode = int(proc.returncode)

    if raise_exception_on_fail and exitcode != 0:
        raise Exception("Running {} resulted in return code {}, below is stderr: \n {}".format(cmd, exitcode, err))

    return (out, err, exitcode)

def runshow(cmd, env=os.environ, cwd='.'):
    # you had better escape cmd cause it's goin to the shell as is

    stdout = sys.stdout
    stderr = sys.stderr

    if LOG != True:
        stdout = None
        strerr = None

    proc = Popen([cmd], stdout=stdout, stderr=stderr, shell=True, env=env, cwd=cwd)
    proc.communicate()

    exitcode = int(proc.returncode)

    return exitcode

def flatwalk_up(haystack, needle):
    results = []
    spl = needle.split("/")
    needle_parts = [spl.pop(0)]
    for s in spl:
        add = "/".join([needle_parts[-1],s])
        needle_parts.append(add)

    for (folder, fn) in flatwalk(haystack):
        for n in needle_parts:
            if folder.endswith(n):
                results.append((folder, fn))
                break
        if folder == haystack:
            results.append((folder, fn))

    for (folder, fn) in results: 
        debug ((folder, fn))
        yield (folder, fn)

def flatwalk(path):
    for (folder, b, c) in os.walk(path):
        for fn in c:
            yield (folder, fn)

def delfiles(d, olderthan_days=30):
    cutoff = (time.time())- olderthan_days * 86400
    for folder, fn in flatwalk(d):
        if os.path.getmtime(os.path.join(folder, fn)) < cutoff:
            shutil.rmtree((os.path.join(folder, fn)))
            os.remove(os.path.join(folder, fn))

def dir_is_git_repo(dir):
    try:
        repo = Repo(dir)
        return True

    except InvalidGitRepositoryError:
        pass

    return False

def git_rootdir(dir="."):
    if dir_is_git_repo(dir):
        return dir
    else:
        #print (wdir)
        oneup = os.path.abspath(dir+'/../')
        if oneup != "/":
            #print ("trying {}".format(oneup))
            return git_rootdir(oneup)
        else:
            # not a git repository
            return None

def git_check(wdir='.'):
    
    git_root = git_rootdir(wdir)

    if git_root == None:
        return 0

    f = "{}/.git/FETCH_HEAD".format(os.path.abspath(git_root))
    
    if os.path.isfile(f):
        '''
         make sure this is not a freshly cloned repo with no FETCH_HEAD
        '''
        last_fetch = int(os.stat(f).st_mtime)
        diff = int(time.time() - last_fetch)
    else:
        # if the repo is a fresh clone, there is no FETCH_HEAD
        # so set time diff to more than a minute to force a fetch
        diff = 61
        
    repo = Repo(git_root)

    assert not repo.bare

    remote_names = []
    
    # fetch at most once per minute
    for r in repo.remotes:
        remote_names.append(r.name)
        if diff > 60:
            remote = Remote(repo, r.name)
            remote.fetch()
        
    # check what branch we're on
    branch = repo.active_branch.name
        
    origin_branch = None
    for ref in repo.git.branch('-r').split('\n'):
        for rn in remote_names:
            if "{}/{}".format(rn, branch) in ref:
                origin_branch = ref.strip()
                break
        
        
    if origin_branch == None:
        # no remote branch to compare to
        return 0
        
    # check if local branch is ahead and /or behind remote branch
    command = "git -C {} rev-list --left-right --count \"{}...{}\"".format(git_root, branch, origin_branch)
    #print command
    (ahead_behind, err, exitcode) = run(command, raise_exception_on_fail=True)
    ahead_behind = ahead_behind.strip().split("\t")
    ahead = int(ahead_behind[0])
    behind = int(ahead_behind.pop())
    
    if behind > 0:
        sys.stderr.write("")
        sys.stderr.write("GIT ERROR: You are on branch {} and are behind the remote.  Please git pull and/or merge before proceeding.  Below is a git status:".format(branch))
        sys.stderr.write("")
        (status, err, exitcode) = run("git -C {} status ".format(git_root))
        sys.stderr.write(status)
        sys.stderr.write("")
        return(-1)
    else:
    
        TB_GIT_DEFAULT_BRANCH = os.getenv('TB_GIT_DEFAULT_BRANCH', 'master')
        
        if branch != TB_GIT_DEFAULT_BRANCH:
            '''
                in this case assume we're on a feature branch
                if the FB is behind master then issue a warning
            '''
            command = "git -C {} branch -vv | grep {} ".format(git_root, TB_GIT_DEFAULT_BRANCH)
            (origin_master, err, exitcode) = run(command)
            if exitcode != 0:
                '''
                In this case the git repo does not contain TB_GIT_DEFAULT_BRANCH, so I guess assume that we're 
                on the default branch afterall and that we're up to date persuant to the above code
                '''
                return 0
            
            for line in origin_master.split("\n"):
                if line.strip().startswith(TB_GIT_DEFAULT_BRANCH):
                    origin = line.strip().split('[')[1].split('/')[0]

            assert origin != None

            command = "git -C {} rev-list --left-right --count \"{}...{}/{}\"".format(git_root, branch, origin, TB_GIT_DEFAULT_BRANCH)
            (ahead_behind, err, exitcode) = run(command)
            ahead_behind = ahead_behind.strip().split("\t")
            ahead = int(ahead_behind[0])
            behind = int(ahead_behind.pop())

            command = "git -C {} rev-list --left-right --count \"{}...{}\"".format(git_root, branch, TB_GIT_DEFAULT_BRANCH)
            (ahead_behind, err, exitcode) = run(command)
            ahead_behind = ahead_behind.strip().split("\t")
            local_ahead = int(ahead_behind[0])
            local_behind = int(ahead_behind.pop())

            
            if behind > 0:
                sys.stderr.write("")
                sys.stderr.write("GIT WARNING: Your branch, {}, is {} commit(s) behind {}/{}.\n".format(branch, behind, origin, TB_GIT_DEFAULT_BRANCH))
                sys.stderr.write("This action may clobber new changes that have occurred in {} since your branch was made.\n".format(TB_GIT_DEFAULT_BRANCH))
                sys.stderr.write("It is recommended that you stop now and merge or rebase from {}\n".format(TB_GIT_DEFAULT_BRANCH))
                sys.stderr.write("\n")
                
                if ahead != local_ahead or behind != local_behind:
                    sys.stderr.write("")
                    sys.stderr.write("INFO: your local {} branch is not up to date with {}/{}\n".format(TB_GIT_DEFAULT_BRANCH, origin, TB_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("HINT:")
                    sys.stderr.write("git checkout {} ; git pull ; git checkout {}\n".format(TB_GIT_DEFAULT_BRANCH, branch))
                    sys.stderr.write("\n")
                    
                answer = raw_input("Do you want to continue anyway? [y/N]? ").lower()
                
                if answer != 'y':
                    log("")
                    log("Aborting due to user input")
                    exit()
            
        return 0


class NoRemoteState(Exception):
    pass

class RemoteStateKeyNotFound(Exception):
    pass

class RemoteStateReader():

    def __init__(self):
        self.components = {}

    def load(self, component):
        if component not in self.components.values():
            u = Utils()
            wt = WrapTerraform(terraform_path=u.terraform_path)

            wt.set_option('-json')
            wt.set_option('-no-color')
            (out, err, exitcode) = run(wt.get_command(command="show", wdir=component))
            if exitcode == 0:
                d = json.loads(out)
                try:
                    self.components[component] = d["values"]["outputs"]
                except KeyError:
                    raise NoRemoteState("ERROR: No remote state found for component {}".format(component))
  
    def value(self, component, key):
        self.load(component)
        
        try:
            value = self.components[component][key]["value"]
        except KeyError:
            msg = "ERROR: State key \"{}\" not found in component {}\nKey must be one of: {}".format(key, component, ", ".join(self.components[component].keys()))
            raise RemoteStateKeyNotFound(msg)

        return value


class WrapTerraform():

    def __init__(self, terraform_path=None):

        if terraform_path == None:
            terraform_path = os.getenv("TERRAFORM_BIN", "terraform")

        self.tf_bin = terraform_path
        self.cli_options = []
        self.quiet = False

    def get_cache_dir(ymlfile, package_name):
        cache_slug = os.path.abspath(ymlfile)
        debug("cache_slug = {}".format(cache_slug))
        return  os.path.expanduser('~/.{}_cache/{}'.format(package_name, hashlib.sha224(cache_slug).hexdigest()))

    def set_option(self, option):
        self.cli_options.append(option)

    def set_quiet(self, which=True):
        self.quiet = which

    def get_command(self, command, wdir=".", var_file=None, extra_args=[]):

        if var_file != None:
            var_file = "-var-file={}".format(var_file)
        else:
            var_file = ""

        cmd = "{} {} {} {} ".format(self.tf_bin, command, wdir, var_file, " ".join(set(self.cli_options)), " ".join(extra_args))
        
        if self.quiet:
            cmd += " > /dev/null 2>&1 "
        
        debug("running command:\n{}".format(cmd))
        return cmd


class ErrorParsingYmlVars(Exception):
    pass

class HclParseException(Exception):
    pass

class Project():

    def __init__(self,
        git_filtered=False,
        conf_marker="project.yml",
        inpattern=".hclt"):

        self.inpattern=inpattern
        self.component_dir=None
        self.vars=None
        self.parse_messages = []

        self.components = None
        self.git_filtered = git_filtered
        self.conf_marker = conf_marker
        self.remotestates = None

    def set_tf_dir(self, dir):
        self.tf_dir = dir

    def set_component_dir(self, dir):
        self.component_dir=dir
        self.vars = None

    def check_hclt_file(self, path):
        only_whitespace = True
        with open(path, 'r') as lines:
            for line in lines:    
                #debug("##{}##".format(line.strip()))     
                if line.strip() != "":
                    only_whitespace = False
                    break
        #debug(only_whitespace)     

        if not only_whitespace:
            with open(path, 'r') as fp:
                try:
                    obj = hcl.load(fp)
                except:
                    raise HclParseException("FATAL: An error occurred while parsing {}\nPlease verify that this file is valid hcl syntax".format(path))

        return only_whitespace

    def check_parsed_file(self, require_remote_state_block=False):
        # this function makes sure that self.outstring contains a legit hcl file with a remote state config
        obj = hcl.loads(self.out_string)

        debug(obj)
        required = ["inputs", "source"]

        if require_remote_state_block:
            required.append("remote_state")

        missing = []
        for r in required:

            try:
                d = obj[r]
            except KeyError:
                missing.append(r)

        if len(missing) > 0:
            return "Component missing block(s): {}.".format(", ".join(missing))

        return True

    def format_hclt_file(self, path):
        log("Formatting {}".format(path))
        only_whitespace = self.check_hclt_file(path)
        if not only_whitespace:
            cmd = "cat \"{}\" | terraform fmt -".format(path)
            (out, err, exitcode) = run(cmd, raise_exception_on_fail=True)

            with open(path, 'w') as fh:
                fh.write(out)
                

    def example_commands(self, command):
        log("")

        for which, component, match in self.get_components():   
            if match:
                s = "{} {} {}".format(PACKAGE, command, component)
                if which == "bundle":
                    s = "{} {} <u><b>{}</u>".format(PACKAGE, command, component)

                log(s)
        log("")
        
    def get_project_root(self, dir=".", fallback_to_git=True):
        d = os.path.abspath(dir)

        if os.path.isfile("{}/{}".format(d, self.conf_marker)):
            return dir
        if fallback_to_git and dir_is_git_repo(dir):
            return dir
        
        oneup = os.path.abspath(dir+'/../')
        if oneup != "/":
            return self.get_project_root(oneup, fallback_to_git)
        
        raise Exception("Could not find a project root directory")

   # def get_filtered_components(wdir, filter):

    def get_components(self, dir='.'):
        if self.components == None:
            self.components = []
            filtered = []
            if self.git_filtered:
                (out, err, exitcode) = run("git status -s -uall", raise_exception_on_fail=True)
                for line in out.split("\n"):
                    p = line.split(" ")[-1]
                    if len(p) > 3:
                        filtered.append(os.path.dirname(p))

            for (dirpath, filename) in flatwalk('.'):
                dirpath = dirpath[2:]
                if filename in ['component.hclt', "bundle.yml"] and len(dirpath) > 0:
                    which = "component"
                    if filename == "bundle.yml":
                        which = "bundle"
                    if self.git_filtered:
                        match = False
                        for f in filtered:
                            if f.startswith(dirpath):
                                match = True
                                break
                        self.components.append((which, dirpath, match))

                    else:
                        self.components.append((which, dirpath, True))
        
        return self.components


    def component_type(self, component, dir='.'):
        for which, c, match in self.get_components(dir=dir):
            if c == component:
                return which

        return None

    def get_bundle(self, wdir):
        components = []

        if wdir[-1] == "*":
            debug("")
            debug("get_bundle wdir {}".format(wdir))
            wdir = os.path.relpath(wdir[0:-1])
            for which, c, match in self.get_components():
                if c.startswith(wdir):
                    components.append(c)

                    debug("get_bundle  {}".format(c))
            debug("")
            return components

        bundleyml = '{}/{}'.format(wdir, "bundle.yml")

        if not os.path.isfile(bundleyml):
            return [wdir]

        with open(bundleyml, 'r') as fh:
            d = yaml.load(fh, Loader=yaml.FullLoader)

        order = d['order']

        if type(order) == list:
            for i in order:
                component = "{}/{}".format(wdir, i)
                if self.component_type(component, wdir) == "component":
                    components.append(component)
                else:
                    for c in  self.get_bundle(component):
                        components.append(c)

        return components

    def check_hclt_files(self):
        for f in self.get_files():
            debug("check_hclt_files() checking {}".format(f))
            self.check_hclt_file(f)

    def get_files(self):
        project_root = self.get_project_root(self.component_dir)
        for (folder, fn) in flatwalk_up(project_root, self.component_dir):
            if fn.endswith(self.inpattern):
                yield "{}/{}".format(folder, fn)

    def get_yml_vars(self):
        if self.vars == None:
            var_sources = {}
            project_root = self.get_project_root(self.component_dir)
            self.vars={}
            for (folder, fn) in flatwalk_up(project_root, self.component_dir):
                if fn.endswith('.yml'):

                    with open(r'{}/{}'.format(folder, fn)) as fh:
                        d = yaml.load(fh, Loader=yaml.FullLoader)
                        if type(d) == dict:
                            for k,v in d.items():
                                if type(v) in (str, int, float):
                                    self.vars[k] = v
                                    var_sources[k] =  '{}/{}'.format(folder, fn)

            # special vars
            self.vars["PROJECT_ROOT"] = project_root
            self.vars["COMPONENT_PATH"] = self.component_path
            self.vars["COMPONENT_DIRNAME"] = self.component_path.split("/")[-1]
            try:
                self.vars["TB_INSTALL_PATH"] = os.path.dirname(os.path.abspath(os.readlink(__file__)))
            except OSError:
                self.vars["TB_INSTALL_PATH"] = os.path.dirname(os.path.abspath(__file__))


            # parse item values
            for i in range(10):
                for k,v in self.vars.items():
                    if "${" in  v:
                        self.vars[k] = self.parsetext(v)

            problems = []

            for k,v in self.vars.items():
                if "${" in  v:
                    msg = self.check_parsed_text(v)
                    if msg != "":
                        problems.append("File {}, cannot parse value of \"{}\"".format(os.path.relpath(var_sources[k]), k))
                        for line in msg.split("\n"):
                            problems.append(line)

            if len(problems) > 0:

                for line in problems:
                    if line != "":
                        sys.stderr.write("\n"+line)
                sys.stderr.write("\n")
                sys.stderr.write("\n")
                raise ErrorParsingYmlVars(" ".join(problems))

            # now for every value that starts with rspath(...), parse
            for k,v in self.vars.items():
                if v.startswith("rspath(") and v.endswith(")"):
                    txt = self.parsetext(v[7:-1])
                    (component, key) = txt.split(":")
                    if self.remotestates == None:
                        self.remotestates = RemoteStateReader()
                    self.vars[k] = self.remotestates.value(component, key)

    def setup_wdir(self):
        debug(self.hclfile)


    def save_outfile(self):
        with open(self.outfile, 'w') as fh:
            fh.write(self.hclfile)

    @property
    def outfile(self):
        return "{}/{}".format(self.root_wdir, "component.hcl")

    @property
    def component_path(self):
        abswdir = os.path.abspath(self.component_dir)
        absroot = self.get_project_root(self.component_dir)

        return abswdir[len(absroot)+1:]

    @property
    def root_wdir(self):
        tf_wdir =  self.tf_dir
        if not os.path.isdir(tf_wdir):
            os.makedirs(tf_wdir)

        return tf_wdir

    def get_template(self):
        self.templates = OrderedDict()
        for f in self.get_files():
            data = u""
            with open(f, 'r') as lines:
                for line in lines:         
                    data += line
                self.templates[os.path.basename(f)] = {
                    "filename": f,
                    "data" : data
                }

    # @property
    # def tfvars_env(self):
    #     self.get_yml_vars()
    #     en = {}

    #     # self.vars
    #     for (k, v) in  self.vars.items():
    #         en['TF_VAR_{}'.format(k)] = v

    #     # ENV VARS
    #     for (k, v) in  os.environ.items():
    #         en['TF_VAR_{}'.format(k)] = v

    #     return en

    # @property
    # def tfvars_tf(self):
    #     out = []
    #     for (k,v) in self.tfvars_env.items():
    #         s = "variable \"{}\" ".format(k[7:]) + '{default = ""}'
    #         out.append(s)

    #     return "\n".join(out)

    def parsetext(self, s):

        # self.vars
        for (k, v) in  self.vars.items():
            s = s.replace('${' + k + '}', v)

        # ENV VARS
        for (k, v) in  os.environ.items():
            s = s.replace('${' + k + '}', v)

        return s

    def check_parsed_text(self, s):
        regex = r"\$\{(.+?)\}"

        # now make sure that all vars have been replaced
        # exclude commented out lines from check
        linenum = 0
        msg = ""
        lines = s.split("\n")
        for line in lines:
            linenum += 1
            try:
                if line.strip()[0] != '#':

                    matches = re.finditer(regex, line)

                    for matchNum, match in enumerate(matches):
                        miss = match.group()

                        if len(lines) > 1:
                            msg += "line {}:".format(linenum)
                        msg += "\n   No substitution found for {}".format(miss)

                        lim = 80
                        near_matches = {}
                        for k in self.vars.keys():
                            ratio = fuzz.ratio(miss, k)
                            if ratio >= lim:
                                near_matches[k] = ratio

                        for k in os.environ.keys():
                            ratio = fuzz.ratio(miss, k)
                            if ratio >= lim:
                                near_matches[k] = ratio

                        for k,ratio in near_matches.items():
                            msg += "\n   ==>  Perhaps you meant ${"+k+"}?"

                        msg += "\n"

            except IndexError: # an empty line has no first character ;)
                pass

        #debug(msg)
        return msg


    def parse_template(self):

        self.check_hclt_files()
        self.get_yml_vars()
        self.get_template()

        self.out_string=u""

        self.parse_messages = []

        for fn,d in self.templates.items():
            parsed = self.parsetext(d['data'])
            msg = self.check_parsed_text(parsed)
            if msg != "":
                self.parse_messages.append("File: {}".format(os.path.relpath(d['filename'])))
                self.parse_messages.append(msg)

            self.out_string += parsed
            self.out_string += "\n"

    @property
    def parse_status(self):
        if len(self.parse_messages) == 0:
            return True

        return "\n".join([u"Could not substitute all variables in templates 😢"] + self.parse_messages)
        

    @property
    def hclfile(self):
        self.parse_template()
        return self.out_string


class ComponentSourceException(Exception):
    pass


class ComponentSource():
    def __init__(self, args) -> None:
        self.args = args

    def set_targetdir(self,targetdir ):
        if not os.path.isdir(targetdir):
            os.makedirs(targetdir)

        self.targetdir = targetdir

    def fetch(self):
        raise ComponentSourceException("not implemented here")

class ComponentSourcePath(ComponentSource):
    
    def fetch(self):
        if "path" not in self.args:
             raise ComponentSourceException("path not present in source block")
        
        if not os.path.isdir(self.args["path"]):
             raise ComponentSourceException("No such directory: {}".format(self.args["path"]))

        shutil.copytree(self.args["path"], self.targetdir, dirs_exist_ok=True)
    

class ComponentSourceGit(ComponentSource):
    def fetch(self):
        if "repo" not in self.args:
             raise ComponentSourceException("repo not present in source block")
        
        t = tempfile.mkdtemp()

        try:
            if "branch" in self.args:
                Repo.clone_from(self.args["repo"], t, branch=self.args["branch"], depth=1)
            else:
                Repo.clone_from(self.args["repo"], t, depth=1)
        except:
            shutil.rmtree(t)
            raise ComponentSourceException("Error cloning git repo {}".format(self.args["repo"]))
        
        if "path" in self.args:

            subdir = "{}/{}".format(t, self.args["path"])
            if not os.path.isdir(subdir):
                shutil.rmtree(t)
                raise ComponentSourceException("No such path {} in repo: {}".format(self.args["path"], self.args["repo"]))

            shutil.copytree(subdir, self.targetdir, dirs_exist_ok=True)

        else:
            shutil.copytree(t, self.targetdir, dirs_exist_ok=True)
    
        shutil.rmtree(t)

class ComponentRemoteState():
    BLOCK_SIZE = 16

    def __init__(self, args, localpath) -> None:
        self.args = args
        self.localpath = localpath
        self.passphrase = None
        self.fetched = False

        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
 
    def set_passphrase(self, passphrase):
        self.passphrase = passphrase
    
    def encrypt(self):
        if self.passphrase == None:
            raise Exception("No passphrase given")
            
        with open(self.localpath, 'r') as fh:
            content = fh.read()
    
        private_key = hashlib.sha256(self.passphrase.encode("utf-8")).digest()
        pad = lambda s: s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)
        padded = pad(content)
        iv = get_random_bytes(AES.block_size)
        cipher = AES.new(private_key, AES.MODE_CBC, iv)
        
        

        ciphertext = cipher.encrypt(bytes(padded.encode('utf-8')))

        with open(self.localpath, 'w') as fh:
            json.dump({'ciphertext':  b64encode(ciphertext).decode('utf-8'), 'iv': b64encode(iv).decode('utf-8')}, fh)
        
    def decrypt(self):
        if self.passphrase == None:
            raise Exception("No passphrase given")
        
        with open(self.localpath, 'rb') as fh:
            obj = json.load(fh)

        unpad = lambda s: s[:-ord(s[len(s) - 1:])]

        try:
            iv = b64decode(obj['iv'])
            ciphertext = b64decode(obj['ciphertext'])

            private_key = hashlib.sha256(self.passphrase.encode("utf-8")).digest()

            cipher = AES.new(private_key, AES.MODE_CBC, iv)

            plaintext = unpad(cipher.decrypt(ciphertext))

            with open(self.localpath, "wb") as fh:
                fh.write(plaintext)

        except (ValueError, KeyError):
            print("Incorrect decryption")
            

    @property
    def is_encrypted(self):

        try:
            with open(self.localpath, 'r') as fh:
                obj = json.load(fh)

            if "ciphertext" in obj:
                return True
        except:
            pass

        return False
    
    def push(self):
        raise Exception("not implemented here")

    def fetch(self):
        raise Exception("not implemented here")
    
class ComponentRemoteStateAwsS3(ComponentRemoteState):
    s3_client = boto3.client('s3')

    def push(self):
        bucket = self.args["bucket"]
        bucket_path = self.args["bucket_path"]
        try:
            response = self.s3_client.upload_file(self.localpath, bucket, "{}/terraform.tfvars".format(bucket_path))
        except ClientError as e:
            debug(e)
            return False
        return True

    def fetch(self):
        bucket = self.args["bucket"]
        bucket_path = self.args["bucket_path"]
    
        with open(self.localpath, 'wb') as fh:
            self.s3_client.download_fileobj(bucket, '{}/terraform.tfvars'.format(bucket_path), fh)

        self.fetched = True

class ComponentRemoteStateAzureStorage(ComponentRemoteState):
    pass

class ComponentRemoteStateFilesystem(ComponentRemoteState):
    def push(self):
        tf_path = self.args["path"]

        if not os.path.isdir(os.path.dirname(tf_path)):
            os.makedirs(os.path.dirname(tf_path))
        
        shutil.copy(self.localpath, tf_path)

    def fetch(self):
        tf_path = self.args["path"]

        if os.path.isfile(tf_path):
            shutil.copy(tf_path, self.localpath)

class Utils():

    conf_dir = os.path.expanduser("~/.config/terrabuddy")
    bin_dir = os.path.expanduser("~/.config/terrabuddy/bin")

    @staticmethod
    def download_progress(url, filename, w=None):
        if w == None:
            rows, columns = os.popen('stty size', 'r').read().split()
            w = int(columns) - 5

        with open(filename, "wb") as f:
           response = requests.get(url, stream=True)
           total_length = response.headers.get('content-length')

           if total_length is None: # no content length header
               f.write(response.content)
           else:
               dl = 0
               total_length = int(total_length)
               for data in response.iter_content(chunk_size=4096):
                   dl += len(data)
                   f.write(data)
                   done = int(w * dl / total_length)
                   sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (w-done)) )    
                   sys.stdout.flush()

        print("")

        
    def __init__(self, terraform_path=None):
        self.terraform_v = None

        conf_file = "{}/config.hcl".format(self.conf_dir)
        if os.path.isfile(conf_file):
            with open(conf_file, 'r') as fp:
                self.conf = hcl.load(fp)
        else:
            self.conf = {}

        try:
            self.bin_dir = os.path.expanduser(self.conf['bin_dir'])
        except:
            pass
        if terraform_path == None:
            terraform_path = "{}/terraform".format(self.bin_dir)
            if not os.path.isdir(self.bin_dir):
                os.makedirs(self.bin_dir)

        self.terraform_path = terraform_path

        if not os.path.isdir(self.conf_dir):
            os.makedirs(self.conf_dir)

    def terraform_currentversion(self):
        if self.terraform_v == None:
            r = requests.get("https://releases.hashicorp.com/terraform/index.json")  
            obj = json.loads(r.content)
            versions = []
            for k in obj['versions'].keys():
                a,b,c = k.split('.')

                try:
                    v1 = "{:05}".format(int(a))
                    v2 = "{:05}".format(int(b))
                    v3 = "{:05}".format(int(c))
                    versions.append("{}.{}.{}".format(v1, v2, v3))
                except ValueError:
                    # if alphanumeric chars in version
                    # this excludes, rc, alpha, beta versions
                    continue

            versions.sort() # newest will be at the end
            v1, v2, v3 = versions.pop(-1).split(".")

            latest = "{}.{}.{}".format(int(v1), int(v2), int(v3))

            url = "https://releases.hashicorp.com/terraform/{}/terraform_{}_linux_amd64.zip".format(latest, latest)

            self.terraform_v = (latest, url)

        return self.terraform_v

    def install(self, update=True):
        debug("install")
        missing, outofdate = self.check_setup(verbose=False, updates=True)

        debug("missing={}".format(missing))
        debug("outofdate={}".format(outofdate))

        if len(missing)+len(outofdate) == 0:
            log("SETUP, Nothing to do. terraform installed and up to date")
        else:
            if "terraform" in missing:
                log("Installing terraform")
                self.install_terraform()
            elif "terraform" in outofdate and update:
                log("Updating terraform")
                self.install_terraform()


    def install_terraform(self, version=None):
        currentver, url = self.terraform_currentversion()
        if version == None:
            version = currentver

        log("Downloading terraform {} to {}...".format(version, self.terraform_path))
        Utils.download_progress(url, self.terraform_path+".zip")

        with zipfile.ZipFile(self.terraform_path+".zip", 'r') as zip_ref:
            zip_ref.extract("terraform", os.path.abspath('{}/../'.format(self.terraform_path) ))
            
        os.chmod(self.terraform_path, 500) # make executable
        os.unlink(self.terraform_path+".zip") # delete zip

    def check_setup(self, verbose=True, updates=True):
        missing = []
        outofdate = []
        debug(self.terraform_path)
        out, err, retcode = run("{} --version".format(self.terraform_path))

        debug("check setup")
        debug((out, err, retcode))

        if retcode == 127:
            missing.append("terraform")
            if verbose:
                log("terraform not installed, you can download it from https://www.terraform.io/downloads.html")
        elif "Your version of Terraform is out of date" in out and updates:
            outofdate.append("terraform")
            if verbose:
                log("Your version of terraform is out of date! You can update by running 'tb --setup', or by manually downloading from https://www.terraform.io/downloads.html")

        return (missing, outofdate)

    def autocheck(self, hours=8):
        check_file = "{}/autocheck_timestamp".format(self.conf_dir)
        if not os.path.isfile(check_file):
            diff = hours*60*60 # 8 hours
        else:
            last_check = int(os.stat(check_file).st_mtime)
            diff = int(time.time() - last_check)

        updates = False
        if diff >= hours*60*60:
            updates = True
            if os.path.isfile(check_file):
                '''
                The previous check file has expired, we want to delete it so that it will be recreated in the block below
                '''
                os.unlink(check_file)

        else:
            debug("last check {} hours ago".format(float(diff)/3600))

        missing, outdated = self.check_setup(verbose=True, updates=updates)
        if len(missing) > 0:
            return -1

        if len(outdated) == 0 and not os.path.isfile(check_file):
            '''
            since checking for updates takes a few seconds, we only want to do this once every 8 hours
            HOWEVER, once the update is available, we want to inform the user on EVERY EXEC, since they might
            not see the prompt immediately. 
            '''
            with open(check_file, "w") as fh:
                pass # check again in 8 hours
            


    def setup(self, args):
        debug("setup")

        if args.setup:
            self.install()

        if args.check_setup:
            missing, outdated = self.check_setup()

            if len(missing) > 0:
                log("CHECK SETUP: MISSING {}".format(", ".join(missing)))

            elif len(outdated) > 0:
                log("CHECK SETUP: UPDATES AVAILABLE")
            else:
                log("terraform installed and up to date")

        else:
            # auto check once every 8 hours
            self.autocheck()

        if args.setup_terraformrc:
            try:
                with open(os.path.expanduser('~/.terraformrc'), 'r') as fh:
                    bashrc = fh.readlines()
            except:
                bashrc = []

            lines = ['plugin_cache_dir = "$HOME/.terraform.d/plugin-cache"']

            with open(os.path.expanduser('~/.terraformrc'), "a") as fh:  
                for l in lines:
                    l = "{}\n".format(l)
                    if l not in bashrc:
                        fh.write(l)
            log("SETUP TERRAFORMRC: OK")

        if args.setup_shell:
            with open(os.path.expanduser('~/.bashrc'), 'r') as fh:
                bashrc = fh.readlines()

            lines = (
                "alias tby='export TB_APPROVE=true'",
                "alias tbn='export TB_APPROVE=false'",
                "alias tbgf='export TB_GIT_FILTER=true'",
                "alias tbgfn='export TB_GIT_FILTER=false'")

            with open(os.path.expanduser('~/.bashrc'), "a") as fh:  
                for l in lines:
                    l = "{}\n".format(l)
                    if l not in bashrc:
                        fh.write(l)
            log("SETUP SHELL: OK")


def main(argv=[]):

    epilog = """The following arguments can be activated using environment variables:

    export TB_DEBUG=y                   # activates debug messages
    export TB_APPROVE=y                 # activates --yes
    export TB_GIT_CHECK=y               # activates --git-check
    export TB_NO_GIT_CHECK=y            # activates --no-git-check
    export TB_MODULES_PATH              # required if using --dev
    export TB_GIT_FILTER                # when displaying components, only show those which have uncomitted git files
    """
    #TGARGS=("--force", "-f", "-y", "--yes", "--clean", "--dev", "--no-check-git")

    f = Figlet(font='slant')

    parser = argparse.ArgumentParser(description='{}\nTB, facilitates terraform with nifty features n such.'.format(f.renderText('terrabuddy')),
    add_help=True,
    epilog=epilog,
    formatter_class=argparse.RawTextHelpFormatter)

    #parser.ArgumentParser(usage='Any text you want\n')

    # subtle bug in ArgumentParser... nargs='?' doesn't work if you parse something other than sys.argv,
    parser.add_argument('command', default=None, nargs='*', help='command to run (apply, destroy, plan, etc)')

    parser.add_argument('--downstream-args', default=None, help='optional arguments to pass downstream to terraform')
    parser.add_argument('--key', default=None, help='optional remote state key to return')

    # booleans
    parser.add_argument('--clean', dest='clean', action='store_true', help='clear all cache')
    parser.add_argument('--force', '--yes', '-t', '-f', action='store_true', help='Perform action without asking for confirmation (same as -auto-approve)')
    parser.add_argument('--dry', action='store_true', help="dry run, don't actually do anything")
    parser.add_argument('--allow-no-remote-state', action='store_true', help="allow components to be run without a remote state block")
    parser.add_argument('--no-check-git', action='store_true', help='Explicitly skip git repository checks')
    parser.add_argument('--check-git', action='store_true', help='Explicitly enable git repository checks')
    parser.add_argument('--git-filter', action='store_true', help='when displaying components, only show those which have uncomitted files in them.')
    parser.add_argument('--quiet', "-q", action='store_true', help='suppress output except fatal errors')
    parser.add_argument('--json', action='store_true', help='When applicable, output in json format')
    parser.add_argument('--list', action='store_true', help='list components in project')
    parser.add_argument('--setup', action='store_true', help='Install terraform')
    parser.add_argument('--check-setup', action='store_true', help='Check if terraform is up to date')
    parser.add_argument('--setup-shell', action='store_true', help='Export a list of handy aliases to the shell.  Can be added to ~./bashrc')
    parser.add_argument('--setup-terraformrc', action='store_true', help='Setup sane terraformrc defaults')
    parser.add_argument('--debug', action='store_true', help='display debug messages')

    clear_cache = False

    args = parser.parse_args(args=argv)
    # TODO add project specific args to project.yml

    global LOG

    if args.quiet or args.json:
        LOG = False

    if args.debug or os.getenv('TB_DEBUG', 'n')[0].lower() in ['y', 't', '1'] :
        global DEBUG
        DEBUG = True
        log("debug mode enabled")

    (exitcode, path, err) = run("which terraform")
    terraform_path = None
    if exitcode == 0:
        terraform_path = path.strip()

    u = Utils(
        terraform_path = os.getenv("TERRAFORM_BIN", terraform_path)
    )
    u.setup(args)

    if args.setup_shell or args.setup_terraformrc or args.check_setup  or args.setup:
        return 0

    # grab args

    git_filtered = str(os.getenv('TB_GIT_FILTER', args.git_filter)).lower()  in ("on", "true", "1", "yes")
    force = str(os.getenv('TB_APPROVE', args.force)).lower()  in ("on", "true", "1", "yes")

    project = Project(git_filtered=git_filtered)
    wt = WrapTerraform(terraform_path=u.terraform_path)

    if args.downstream_args != None:
        wt.set_option(args.downstream_args)

    if len(args.command) < 2:

        if args.list:
            for which, component, match in project.get_components():     
                print(component)
            return 0

        log("ERROR: no command specified, see help")
        return(-1)
    else:
        command = args.command[1]

    if command == "terraform":
        print(u.terraform_path)
        return 0

    CHECK_GIT = True
    if command[0:5] in ('apply', 'destr'):
        # [0:5] to also include "*-all" command variants
        CHECK_GIT = True

    if args.check_git or os.getenv('TB_GIT_CHECK', 'n')[0].lower() in ['y', 't', '1']:
        CHECK_GIT = True

    if args.no_check_git or os.getenv('TB_NO_GIT_CHECK', 'n')[0].lower() in ['y', 't', '1'] :
        CHECK_GIT = False

    # check git
    if CHECK_GIT:
        gitstatus = git_check()
        if gitstatus != 0:
            return gitstatus


    #TODO add "env" command to show the env vars with optional --export command for exporting to bash env vars

    if command == "format":
        for (dirpath, filename) in flatwalk('.'):
            if filename.endswith('.hclt'):
                project.format_hclt_file("{}/{}".format(dirpath, filename))
    
    # if command == "parse":
    #     try:
    #         wdir = os.path.relpath(args.command[2])
    #     except:
    #         # no component provided, loop over all and parse them


    if command in ("plan", "apply", "destroy", "refresh", "show", "force-unlock", "parse", "showvars"):

        try:
            cdir = os.path.relpath(args.command[2])
        except:
            log("OOPS, no component specified, try one of these (bundles are <u><b>bold underlined</b>):")
            project.example_commands(command)
            return(100)

        if not os.path.isdir(cdir):
            log("ERROR: {} is not a directory".format(cdir))
            return -1
        
        project.set_component_dir(cdir)

        #here we make tf working dir
        tf_wdir = os.getenv("TG_WORKING_DIR", None)

        if tf_wdir == None:
            current_date_slug = datetime.date.today().strftime('%Y-%m-%d')

            project_abspath = os.path.abspath(project.get_project_root())
            project_slug = hashlib.sha224(project_abspath.encode('utf-8')).hexdigest()
            cdir_relproject = os.path.abspath(os.getcwd())[len(project_abspath)+1:]+'/'+cdir
            cdir_slug = cdir_relproject.replace('/', '_')

            tf_wdir_root = os.path.expanduser('~/.cache/terrabuddy/')
            tf_wdir_p = '{}/{}/{}'.format(tf_wdir_root, project_slug, current_date_slug)

            tf_wdir = '{}/{}'.format(tf_wdir_p, cdir_slug,  str(time.time()))

            if not os.path.isdir(tf_wdir_p):
                # first time today tb has been run, clean up past cache
                delfiles(tf_wdir_root, 30)

            if os.path.isdir(tf_wdir):
                shutil.rmtree(tf_wdir)

            os.makedirs(tf_wdir)

        debug("setting tf_wdir to {}".format(tf_wdir))
        project.set_tf_dir(tf_wdir)

        # -auto-approve and refresh|plan do not mix
        if command in ["refresh", "plan"]:
            force = False

        if force:
            wt.set_option("-auto-approve")

        if args.quiet:
            wt.set_quiet()

        t = project.component_type(component=cdir)
        if t == "component":
            project.parse_template()
            project.setup_wdir() # invoke componentsource
            project.save_outfile()

            if command == "showvars":
                if args.json:
                    print (json.dumps(project.vars, indent=4))
                else:
                    keys = list(project.vars.keys())#.sorted()
                    keys.sort()
                    for k in keys:
                        print ("{}={}".format(k, project.vars[k]))
                    #print(json.dumps(project.vars, indent=4))
                return 0

            if project.parse_status != True:
                print (project.parse_status)
                return (120)

            if command == "parse":
                # we have parsed, our job here is done
                return 0

            check = project.check_parsed_file(require_remote_state_block=not args.allow_no_remote_state)
            if check != True:
                print ("An error was found after parsing {}: {}".format(project.outfile, check))
                return 110

            if args.key != None:
                rs = RemoteStateReader()
                print(rs.value(cdir, args.key))
                return 0
            else:
                if args.json:
                    wt.set_option('-json')
                    wt.set_option('-no-color')

                if not args.dry:

                    # instanciate ComponentSource

                    obj = hcl.loads(project.hclfile)
                    debug(obj)
                    if "source" not in obj:
                        raise Exception("No source block specified in component")
                    if "repo" in obj["source"]:
                        cs = ComponentSourceGit(args=obj["source"])

                    elif "path" in obj["source"]:
                        cs = ComponentSourcePath(args=obj["source"])

                    else:
                        raise Exception("No ComponentSource handler for component")
                    
                    # fetch into tf_wdir
                    cs.set_targetdir(tf_wdir)
                    cs.fetch()


                    # extract inputs into tfvars
                    with open("{}/terraform.tfvars".format(tf_wdir), "w") as fh:
                        for k,v in obj["inputs"].items():
                            fh.write("{} = \"{}\"".format(k,v.replace('"', '\\"')))
                            fh.write("\n")

                    # terraform init
                    cmd =  "{} init ".format(wt.tf_bin)
                    
                    exitcode = runshow(cmd, cwd=tf_wdir)
                    
                    # touch tfstate
                    tfstate_file = "{}/terraform.tfstate".format(tf_wdir)
                    Path(tfstate_file).touch()

                    cmd =  "{} plan -out tfplan -state=terraform.tfstate".format(wt.tf_bin)
                    exitcode = runshow(cmd, cwd=tf_wdir)

                    cmd =  "{} apply tfplan".format(wt.tf_bin)
                    exitcode = runshow(cmd, cwd=tf_wdir)

                    return
                    
                    wt.get_command(command="init", wdir=tf_wdir)

                    # get tfstate

                    # terraform plan apply

                    # save tfstate

                    cmd =  wt.get_command(command=command, wdir=cdir)
                    debug("cmd = {}".format(cmd))           
                    runshow(cmd)
        elif t == "bundle":
            log("Performing {} on bundle {}".format(command, cdir))
            log("")
            # parse first
            parse_status = []
            components = project.get_bundle(cdir)
            for component in components:
                project.set_component_dir(component)
                project.parse_template()
                project.save_outfile()
                if project.parse_status != True:

                    parse_status.append(project.parse_status)

            if len(parse_status) > 0:
                print("\n".join(parse_status))
                return (120)

            if command == "parse":
                # we have parsed, our job here is done
                return 0

            if command == "destroy":
                # destroy in opposite order
                components.reverse()

            # run terraform per component
            for component in components:                

                log("{} {} {}".format(PACKAGE, command, component))
                if args.dry:
                    continue

                if command == "show":
                    continue

                debug("run terraform per component")
                retcode = runshow(wt.get_command(command=command, wdir=component))

                if retcode != 0:
                    log("Got a non zero return code running component {}, stopping bundle".format(component))
                    return retcode

            if command in ['apply', "show"] and not args.dry:
                log("")
                log("")

                # grab outputs of components
                out_dict = []
                
                # fresh instance of WrapTerraform to clear out any options from above that might conflict with show
                wt = WrapTerraform(terraform_path=u.terraform_path)
                if args.downstream_args != None:
                    wt.set_option(args.downstream_args)

                if args.json:
                    wt.set_option('-json')
                    wt.set_option('-no-color')

                for component in components:

                    out, err, retcode = run(wt.get_command(command="show", wdir=component), raise_exception_on_fail=True)

                    if args.json:
                        d = json.loads(out)
                        out_dict.append({
                            "component" : component,
                            "outputs" : d["values"]["outputs"]})
                    else:
                        debug((out, err, retcode))

                        lines = []

                        p = False
                        for line in out.split("\n"):

                            if p:
                                lines.append("    {}".format(line))
                            if line.strip().startswith('Outputs:'):
                                debug("Outputs:; p = True")
                                p = True

                        txt = "| {}".format(component)
                        print("-" * int(len(txt)+3))
                        print(txt)
                        print("-" * int(len(txt)+3))

                        if len(lines) > 0:
                            print("  Outputs:")
                            print("")
                            for line in lines:
                                print(line)

                        else:
                            print("No remote state found")
                        print("")
                if args.json:
                    print(json.dumps(out_dict, indent=4))

        else:
            log("ERROR {}: this directory is neither a component nor a bundle, nothing to do".format(cdir))
            return 130
            

def cli_entrypoint():
    retcode = main(sys.argv)
    exit(retcode)

if __name__ == '__main__':
    retcode = main(sys.argv)
    exit(retcode)
