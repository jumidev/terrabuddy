#!/usr/bin/env python3

import json, os, sys, yaml, hcl
from fuzzywuzzy import fuzz
import argparse, glob
from subprocess import Popen, PIPE

from collections import OrderedDict
import re

from git import Repo, Remote, InvalidGitRepositoryError
import time

PACKAGE = "oosh"
LOG = True
DEBUG=False

def anyof(needles, haystack):
    for n in needles:
        if n in haystack:
            return True

    return False

def log(s):
    if LOG == True:
        print (s)

def debug(s):
    if DEBUG == True:
        print (s)

def run(cmd, splitlines=False, env=os.environ):
    # you had better escape cmd cause it's goin to the shell as is
    proc = Popen([cmd], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True, env=env)
    out, err = proc.communicate()
    if splitlines:
        out_split = []
        for line in out.split("\n"):
            line = line.strip()
            if line != '':
                out_split.append(line)
        out = out_split

    exitcode = int(proc.returncode)

    return (out, err, exitcode)

def runshow(cmd, env=os.environ):
    # you had better escape cmd cause it's goin to the shell as is

    stdout = sys.stdout
    stderr = sys.stderr

    if LOG != True:
        stdout = None
        strerr = None

    proc = Popen(cmd, stdout=stdout, stderr=stderr, shell=True, env=env)
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
        yield (folder, fn)

def flatwalk(path):
    for (folder, b, c) in os.walk(path):
        for fn in c:
            yield (folder, fn)

def example_commands(command):
    git_filtered=os.getenv('OOSH_GIT_FILTER', "False").lower()  in ("on", "true", "1")

    filtered = []
    if git_filtered:
        (out, err, exitcode) = run("git status -s -uall")
        for line in out.split("\n"):
            p = line.split(" ")[-1]
            if len(p) > 3:
                filtered.append(os.path.dirname(p))

    log("")

    for (dirpath, filename) in flatwalk('.'):
        dirpath = dirpath[2:]
        if filename in ['terragrunt.hclt'] and len(dirpath) > 0:
            if git_filtered:
                match = False
                for f in filtered:
                    if f.startswith(dirpath):
                        match = True
                        break
                if match:
                    log("{} {} {}".format(PACKAGE, command, dirpath))

            else:
                log("{} {} {}".format(PACKAGE, command, dirpath))
    log("")


def get_project_root(dir=".", fallback_to_git=True, conf_marker="oosh.yml"):
    d = os.path.abspath(dir)

    if os.path.isfile("{}/{}".format(d, conf_marker)):
        return dir
    if fallback_to_git and dir_is_git_repo(dir):
        return dir
    
    oneup = os.path.abspath(dir+'/../')
    if oneup != "/":
        return get_project_root(oneup, fallback_to_git, conf_marker)
    
    raise "Could not find a project root directory"

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
    (ahead_behind, err, exitcode) = run(command)
    ahead_behind = ahead_behind.strip().split("\t")
    ahead = int(ahead_behind[0])
    behind = int(ahead_behind.pop())
    
    if exitcode != 0:
        # if exitcode is not zero something serious went wrong
        raise("An error occurred while running '{}'\n\n".format( command, err))
    else:
        if behind > 0:
            sys.stderr.write("")
            sys.stderr.write("GIT ERROR: You are on branch {} and are behind the remote.  Please git pull and/or merge before proceeding.  Below is a git status:".format(branch))
            sys.stderr.write("")
            (status, err, exitcode) = run("git -C {} status ".format(git_root))
            sys.stderr.write(status)
            sys.stderr.write("")
            return(-1)
        else:
        
            OOSH_GIT_DEFAULT_BRANCH = os.getenv('OOSH_GIT_DEFAULT_BRANCH', 'master')
            
            if branch != OOSH_GIT_DEFAULT_BRANCH:
                '''
                 in this case assume we're on a feature branch
                 if the FB is behind master then issue a warning
                '''
                command = "git -C {} branch -vv | grep {} ".format(git_root, OOSH_GIT_DEFAULT_BRANCH)
                (origin_master, err, exitcode) = run(command)
                if exitcode != 0:
                    '''
                    In this case the git repo does not contain OOSH_GIT_DEFAULT_BRANCH, so I guess assume that we're 
                    on the default branch afterall and that we're up to date persuant to the above code
                    '''
                    return 0
                
                for line in origin_master.split("\n"):
                    if line.strip().startswith(OOSH_GIT_DEFAULT_BRANCH):
                        origin = line.strip().split('[')[1].split('/')[0]

                assert origin != None

                command = "git -C {} rev-list --left-right --count \"{}...{}/{}\"".format(git_root, branch, origin, OOSH_GIT_DEFAULT_BRANCH)
                (ahead_behind, err, exitcode) = run(command)
                ahead_behind = ahead_behind.strip().split("\t")
                ahead = int(ahead_behind[0])
                behind = int(ahead_behind.pop())

                command = "git -C {} rev-list --left-right --count \"{}...{}\"".format(git_root, branch, OOSH_GIT_DEFAULT_BRANCH)
                (ahead_behind, err, exitcode) = run(command)
                ahead_behind = ahead_behind.strip().split("\t")
                local_ahead = int(ahead_behind[0])
                local_behind = int(ahead_behind.pop())

                
                if behind > 0:
                    sys.stderr.write("")
                    sys.stderr.write("GIT WARNING: Your branch, {}, is {} commit(s) behind {}/{}.\n".format(branch, behind, origin, OOSH_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("This action may clobber new changes that have occurred in {} since your branch was made.\n".format(OOSH_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("It is recommended that you stop now and merge or rebase from {}\n".format(OOSH_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("\n")
                    
                    if ahead != local_ahead or behind != local_behind:
                        sys.stderr.write("")
                        sys.stderr.write("INFO: your local {} branch is not up to date with {}/{}\n".format(OOSH_GIT_DEFAULT_BRANCH, origin, OOSH_GIT_DEFAULT_BRANCH))
                        sys.stderr.write("HINT:")
                        sys.stderr.write("git checkout {} ; git pull ; git checkout {}\n".format(OOSH_GIT_DEFAULT_BRANCH, branch))
                        sys.stderr.write("\n")
                        
                    answer = raw_input("Do you want to continue anyway? [y/N]? ").lower()
                    
                    if answer != 'y':
                        log("")
                        log("Aborting due to user input")
                        exit()
            
        return 0


def check_hclt_file(path):
    only_whitespace = True
    with open(path, 'r') as lines:
        for line in lines:         
            if line.strip != "":
                only_whitespace = False
                break
    if not only_whitespace:
        with open(path, 'r') as fp:
            try:
                obj = hcl.load(fp)
            except:
                raise Exception("FATAL: An error occurred while parsing {}\nPlease verify that this file is valid hcl syntax".format(f))

def format_hclt_file(path):
    log("Formatting {}".format(path))
    check_hclt_file(path)
    cmd = "cat \"{}\" | terraform fmt -".format(path)
    (out, err, exitcode) = run(cmd)

    if exitcode == 0:
        with open(path, 'w') as fh:
            fh.write(out)
        
    else:
        raise Exception(err)

class WrapTerragrunt():

    def __init__(self):

        self.tg_bin = os.getenv("TERRAGRUNT_BIN", "terragrunt")
        self.tf_bin = os.getenv("TERRAFORM_BIN", "terraform")
        self.terragrunt_options = []


    def get_cache_dir(ymlfile, package_name):
        cache_slug = os.path.abspath(ymlfile)
        debug(cache_slug)
        return  os.path.expanduser('~/.{}_cache/{}'.format(package_name, hashlib.sha224(cache_slug).hexdigest()))

    def set_option(self, option):
        self.terragrunt_options.append(option)

    def get_download_dir(self):
        return os.getenv('TERRAGRUNT_DOWNLOAD_DIR',"~/.terragrunt")

    def set_iam_role(self, iam_role):
        self.set_option("--terragrunt-iam-role {} ".format(iam_role))

    def get_command(self, command, wdir=".", var_file=None, extra_args=[]):

        self.set_option("--terragrunt-download-dir {}".format(self.get_download_dir()))
        # path to terraform
        self.set_option("--terragrunt-tfpath {}".format(self.tf_bin))

        if var_file != None:
            var_file = "-var-file={}".format(var_file)
        else:
            var_file = ""

        cmd = "{} {} --terragrunt-source-update --terragrunt-working-dir {} {} {} {} ".format(self.tg_bin, command, wdir, var_file, " ".join(self.terragrunt_options), " ".join(extra_args))
        debug("running command:\n{}".format(cmd))
        return cmd

class TemplateParser():

    def __init__(self, inpattern=".hclt", dir=os.getcwd()):
        self.inpattern=inpattern
        self.dir=dir
        self.vars=None
        self.parse_messages = []


    def get_yml_vars(self):
        if self.vars == None:
            git_root = get_project_root(self.dir)
            self.vars={}
            for (folder, fn) in flatwalk_up(git_root, self.dir):
                if fn.endswith('.yml'):

                    with open(r'{}/{}'.format(folder, fn)) as file:
                        d = yaml.load(file, Loader=yaml.FullLoader)

                        for k,v in d.items():
                            if type(v) in (str, int, float):
                                self.vars[k] = v

    def save_outfile(self):
        f = "{}/{}".format(self.dir, "terragrunt.hcl")
        with open(f, 'w') as fh:
            fh.write(self.hclfile)

    @property
    def component_path(self):
        abswdir = os.path.abspath(self.dir)
        absroot = get_project_root(self.dir)

        return abswdir[len(absroot)+1:]

    def check_hclt_files(self):
        for f in self.get_files():
            debug("check_hclt_files() checking {}".format(f))
            check_hclt_file(f)

    def get_files(self):
        git_root = get_project_root(self.dir)
        for (folder, fn) in flatwalk_up(git_root, self.dir):
            if fn.endswith(self.inpattern):
                yield "{}/{}".format(folder, fn)

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

    @property
    def oosh_vars_generator(self):

        return """
        generate "oosh_vars" {
        path = "oosh_vars.tf"
        if_exists = "overwrite_terragrunt"
        contents = <<EOF
        """+self.tfvars_tf+"\nEOF\n}"


    @property
    def tfvars_env(self):
        self.get_yml_vars()
        en = {}

        # self.vars
        for (k, v) in  self.vars.items():
            en['TF_VAR_{}'.format(k)] = v

        # ENV VARS
        for (k, v) in  os.environ.items():
            en['TF_VAR_{}'.format(k)] = v

        return en

    @property
    def tfvars_tf(self):
        out = []
        for (k,v) in self.tfvars_env.items():
            s = "variable \"{}\" ".format(k[7:]) + '{default = ""}'
            out.append(s)

        return "\n".join(out)

    def parse(self):

        self.check_hclt_files()
        self.get_yml_vars()
        self.get_template()

        self.out_string=u""

        # special vars
        self.vars["COMPONENT_PATH"] = self.component_path
        self.vars["COMPONENT_DIRNAME"] = self.component_path.split("/")[-1]
        self.vars["OOSH_INSTALL_PATH"] = os.path.dirname(os.path.abspath(os.readlink(__file__)))

        self.parse_messages = []
        regex = r"\$\{(.+?)\}"

        for fn,d in self.templates.items():
            # self.vars
            for (k, v) in  self.vars.items():
                d['data'] = d['data'].replace('${' + k + '}', v)

            # ENV VARS
            for (k, v) in  os.environ.items():
                d['data'] = d['data'].replace('${' + k + '}', v)


            # now make sure that all vars have been replaced
            # exclude commented out lines from check
            linenum = 0
            msg = None
            for line in d['data'].split("\n"):
                linenum += 1
                try:
                    if line.strip()[0] != '#':

                        matches = re.finditer(regex, line)

                        for matchNum, match in enumerate(matches):
                            miss = match.group()

                            msg = "{} line {}:".format(d['filename'], linenum)
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
                            self.parse_messages.append(msg)

                except IndexError: # an empty line has no first character ;)
                    pass
         

            self.out_string += d['data']
            self.out_string += "\n"

    @property
    def parse_status(self):
        if len(self.parse_messages) == 0:
            return True

        return "\n".join([u"Could not substitute all variables in templates 😢"] + self.parse_messages)
        

    @property
    def hclfile(self):
        self.parse()
        return self.out_string# + "\n" + self.oosh_vars_generator




def main(argv=[]):

    epilog = """The following arguments can be activated using environment variables:

    export OOSH_DEBUG=y                   # activates debug messages
    export OOSH_APPLY=y                   # activates --force
    export OOSH_APPROVE=y                 # activates --force
    export OOSH_GIT_CHECK=y               # activates --git-check
    export OOSH_NO_GIT_CHECK=y            # activates --no-git-check
    export OOSH_MODULES_PATH              # required if using --dev

    """
    #TGARGS=("--force", "-f", "-y", "--yes", "--clean", "--dev", "--no-check-git")

    parser = argparse.ArgumentParser(description='TG, facilitates calling terragrunt with nifty features n such.', add_help=True, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    # subtle bug in ArgumentParser... nargs='?' doesn't work if you parse something other than sys.argv,
    parser.add_argument('command', default=None, nargs='*', help='terragrunt command to run (apply, destroy, plan, etc)')

    #parser.add_argument('--dev', default=None, help="if in dev mode, which dev module path to reference (OOSH_MODULES_PATH env var must be set and point to your local terragrunt repository path)")
    parser.add_argument('--downstream-args', default=None, help='optional arguments to pass downstream to terragrunt and terraform')

    # booleans
    parser.add_argument('--clean', dest='clean', action='store_true', help='clear all cache')
    parser.add_argument('--force', '--yes', '-t', '-f', action='store_true', help='Perform terragrunt action without asking for confirmation (same as --terragrunt-non-interactive)')
    parser.add_argument('--dry', action='store_true', help="dry run, don't actually do anything")
    parser.add_argument('--no-check-git', action='store_true', help='Explicitly skip git repository checks')
    parser.add_argument('--check-git', action='store_true', help='Explicitly enable git repository checks')
    parser.add_argument('--quiet', action='store_true', help='suppress output except fatal errors')
    parser.add_argument('--debug', action='store_true', help='display debug messages')

    clear_cache = False

    args = parser.parse_args(args=argv)
    # TODO add project specific args to oosh.yml

    if args.quiet:
        LOG = None
        TERRAGRUNT_REDIRECT = " > /dev/null 2>&1 "

    # grab args
    
    if len(args.command) < 2:
        log("ERROR: no command specified, see help")
        return(-1)
    else:
        command = args.command[1]

    CHECK_GIT = True
    if command[0:5] in ('apply', 'destr'):
        # [0:5] to also include "*-all" command variants
        CHECK_GIT = True

    if args.check_git or os.getenv('OOSH_GIT_CHECK', 'n')[0].lower() in ['y', 't', '1']:
        CHECK_GIT = True

    if args.no_check_git or os.getenv('OOSH_NO_GIT_CHECK', 'n')[0].lower() in ['y', 't', '1'] :
        CHECK_GIT = False

    if args.debug or os.getenv('OOSH_DEBUG', 'n')[0].lower() in ['y', 't', '1'] :
        global DEBUG
        DEBUG = True

    # check git
    if CHECK_GIT:
        gitstatus = git_check()
        if gitstatus != 0:
            return gitstatus

    #TODO add "env" command to show the env vars with optional --export command for exporting to bash env vars

    if command == "format":
        for (dirpath, filename) in flatwalk('.'):
            if filename.endswith('.hclt'):
                format_hclt_file("{}/{}".format(dirpath, filename))


    if command in ("plan", "apply", "destroy", "refresh", "show"):
        try:
            WDIR = args.command[2]
        except:
            log("OOPS, no component specified, try one of these:")
            example_commands(command)
            return(100)
            
        tp = TemplateParser(dir=WDIR)
        tp.parse()

        tp.save_outfile()

        if tp.parse_status != True:
            print (tp.parse_status)
            return (120)

        wt = WrapTerragrunt()

        runenv = os.environ.copy

        runshow(wt.get_command(command=command, wdir=WDIR))


if __name__ == '__main__':
    retcode = main(sys.argv)
    exit(retcode)


"""

def get_terragrunt_download_dir():
    terragrunt_dl_dir = " ~/.terragrunt"
    try:
        terragrunt_dl_dir = os.environ['TERRAGRUNT_DOWNLOAD_DIR']
    except:
        pass
    return terragrunt_dl_dir





        self.set_tg_option("--terragrunt-download-dir {}".format(get_terragrunt_download_dir()))


        OOSH_BIN = self.get_terragrunt_bin(WDIR)
        TF_BIN = self.get_terraform_bin(WDIR)
        self.set_tg_option("--terragrunt-tfpath {}".format(TF_BIN))


    def get_bin(self, which, wdir):
        if not os.path.isdir(os.path.abspath(wdir)):
            raise Exception("ERROR: {} is not a dir".format(wdir))
        elif os.path.isfile(wdir + "/" + "terraform.tfvars"):
            if which == "terraform":
                debug("{} requires terraform@0.11".format(wdir))
                return self.TF011_BIN
            else:
                debug("{} requires terragrunt@0.18".format(wdir))
                return self.TG018_BIN

        elif os.path.isfile(wdir + "/" + "terragrunt.hcl"):

            if which == "terraform":
                return self.TF_BIN
            else:
                return self.OOSH_BIN

        else:
            if self.command[-4:] == "-all":
                # scan every subdir looking for modules to tell us what version to use :)
                answers = []
                for i in os.listdir(wdir):
                    p = "{}/{}".format(wdir, i)
                    if os.path.isdir(p):
                        try:
                            answers.append(self.get_bin(which, p))
                        except:
                            pass

                if len(answers) == 0:
                    raise Exception("ERROR: No modules found in {}".format(wdir))

                # turning into a set makes the values unique
                if len(set(answers)) == 1:
                    # only one unique answer
                    return answers[0]

                # if you make it here then LOL
                raise Exception("ERROR: Cannot run {} in {}.  Some modules contain newer terragrunt.hcl files whereas others have the old style terraform.tfvars.  You must run individual {} commands.".format(self.command, wdir, self.command.split('-')[0]))

            else:
                raise Exception("ERROR: {} is not a module".format(wdir))





    def get_terragrunt_bin(self, wdir):
        return self.get_bin("terragrunt", wdir)

    def get_terraform_bin(self, wdir):
        return self.get_bin("terraform", wdir)


"""