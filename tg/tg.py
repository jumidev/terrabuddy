#!/usr/bin/env python3

import json, os, sys
import argparse, glob

from git import Repo, Remote, InvalidGitRepositoryError
import time

PACKAGE = "tg"
LOG = True

def anyof(needles, haystack):
    for n in needles:
        if n in haystack:
            return True

    return False

def log(str):
    if LOG == True:
        print (str)


def flatwalk(path):
    for (folder, b, c) in os.walk(path):
        for fn in c:
            yield (folder[2:], fn)

def example_commands(command):
    git_filtered=os.getenv('TG_GIT_FILTER', "False").lower()  in ("on", "true", "1")

    filtered = []
    if git_filtered:
        (out, err, exitcode) = tg.run("git status -s -uall")
        for line in out.split("\n"):
            p = line.split(" ")[-1]
            if len(p) > 3:
                filtered.append(os.path.dirname(p))

    log("")
    for (dirpath, filename) in flatwalk('.'):
        if filename in ('terraform.tfvars', 'terragrunt.hcl') and len(dirpath) > 0:
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

def git_check(wdir='.'):
    
    f = "{}/.git/FETCH_HEAD".format(os.path.abspath(wdir))
    
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
        
    try:
        repo = Repo(wdir)
    except InvalidGitRepositoryError:
        #print (wdir)
        oneup = os.path.abspath(wdir+'/../')
        if oneup != "/":
            #print ("trying {}".format(oneup))
            return git_check(oneup)

        return 0

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
    command = "git -C {} rev-list --left-right --count \"{}...{}\"".format(wdir, branch, origin_branch)
    #print command
    (ahead_behind, err, exitcode) = tg.run(command)
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
            (status, err, exitcode) = tg.run("git -C {} status ".format(wdir))
            sys.stderr.write(status)
            sys.stderr.write("")
            return(-1)
        else:
        
            TG_GIT_DEFAULT_BRANCH = os.getenv('TG_GIT_DEFAULT_BRANCH', 'master')
            
            if branch != TG_GIT_DEFAULT_BRANCH:
                '''
                 in this case assume we're on a feature branch
                 if the FB is behind master then issue a warning
                '''
                command = "git -C {} branch -vv | grep {} ".format(wdir, TG_GIT_DEFAULT_BRANCH)
                (origin_master, err, exitcode) = tg.run(command)
                if exitcode != 0:
                    '''
                    In this case the git repo does not contain TG_GIT_DEFAULT_BRANCH, so I guess assume that we're 
                    on the default branch afterall and that we're up to date persuant to the above code
                    '''
                    return 0
                
                for line in origin_master.split("\n"):
                    if line.strip().startswith(TG_GIT_DEFAULT_BRANCH):
                        origin = line.strip().split('[')[1].split('/')[0]

                assert origin != None

                command = "git -C {} rev-list --left-right --count \"{}...{}/{}\"".format(wdir, branch, origin, TG_GIT_DEFAULT_BRANCH)
                (ahead_behind, err, exitcode) = tg.run(command)
                ahead_behind = ahead_behind.strip().split("\t")
                ahead = int(ahead_behind[0])
                behind = int(ahead_behind.pop())

                command = "git -C {} rev-list --left-right --count \"{}...{}\"".format(wdir, branch, TG_GIT_DEFAULT_BRANCH)
                (ahead_behind, err, exitcode) = tg.run(command)
                ahead_behind = ahead_behind.strip().split("\t")
                local_ahead = int(ahead_behind[0])
                local_behind = int(ahead_behind.pop())

                
                if behind > 0:
                    sys.stderr.write("")
                    sys.stderr.write("GIT WARNING: Your branch, {}, is {} commit(s) behind {}/{}.\n".format(branch, behind, origin, TG_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("This action may clobber new changes that have occurred in {} since your branch was made.\n".format(TG_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("It is recommended that you stop now and merge or rebase from {}\n".format(TG_GIT_DEFAULT_BRANCH))
                    sys.stderr.write("\n")
                    
                    if ahead != local_ahead or behind != local_behind:
                        sys.stderr.write("")
                        sys.stderr.write("INFO: your local {} branch is not up to date with {}/{}\n".format(TG_GIT_DEFAULT_BRANCH, origin, TG_GIT_DEFAULT_BRANCH))
                        sys.stderr.write("HINT:")
                        sys.stderr.write("git checkout {} ; git pull ; git checkout {}\n".format(TG_GIT_DEFAULT_BRANCH, branch))
                        sys.stderr.write("\n")
                        
                    answer = raw_input("Do you want to continue anyway? [y/N]? ").lower()
                    
                    if answer != 'y':
                        log("")
                        log("Aborting due to user input")
                        exit()
            
        return 0
        
        


class WrapTerragrunt():

    def __init__(self):

        self.tg_bin = os.getenv("TERRAGRUNT_BIN", "terragrunt")
        self.tf_bin = os.getenv("TERRAFORM_BIN", "terraform")
        self.terragrunt_options = []


    def get_cache_dir(ymlfile, package_name):
        cache_slug = os.path.abspath(ymlfile)
        debug(cache_slug)
        return  os.path.expanduser('~/.{}_cache/{}'.format(package_name, hashlib.sha224(cache_slug).hexdigest()))

    def set_terragrunt_option(self, option):
        self.terragrunt_options.append(option)

    def get_terragrunt_command(self):
        return "{} {} "

    def get_terragrunt_download_dir(self):
        return os.getenv('TERRAGRUNT_DOWNLOAD_DIR',"~/.terragrunt")

        
    def get_terragrunt_command(self, command_override=None, wdir=None, var_file=None, extra_args=[]):

        self.set_terragrunt_option("--terragrunt-download-dir {}".format(self.get_terragrunt_download_dir()))

        iam_role = None

        if WDIR != None:
            iam_role=self.get_iam_role
        if iam_role != None:
            # override IAM role from global context if we resolved one from the working dir path
            iam_role = "--terragrunt-iam-role {} ".format(iam_role)
        elif self.IAM_ROLE != None:
            iam_role = "--terragrunt-iam-role {} ".format(self.IAM_ROLE)
        else:
            iam_role = ""

        if CMD == None:
            CMD = self.CMD

        if WDIR == None:
            WDIR = self.WDIR

        if var_file != None:
            var_file = "-var-file={}".format(var_file)
        else:
            var_file = ""

        TG_BIN = self.get_terragrunt_bin(WDIR)
        TF_BIN = self.get_terraform_bin(WDIR)
        self.set_tg_option("--terragrunt-tfpath {}".format(TF_BIN))

        TG_CMD = "{} {} --terragrunt-source-update --terragrunt-working-dir {} {} {} {} {} ".format(TG_BIN, CMD, WDIR, iam_role, var_file, " ".join(self.TG_OPTIONS), " ".join(extra_args))
        debug("running command:\n{}".format(TG_CMD))
        return TG_CMD

class TemplateParser():

    def __init__(self, outfile="terragrunt.hcl", inpattern="*.tpl", dir=os.getcwd()):
        self.inpattern=inpattern
        self.outfile=outfile
        self.dir=dir
        self.special_filenames = ('inputs')

    def save_outfile(self):
        with open(self.outfile, 'w') as fh:
            fh.write(self.out_string)

    def get_files(self):
        return glob.glob(self.inpattern)

    def parse(self):
        self.out_string=u""

        for f in self.get_files():
            f2 = os.path.basename(f).split('.')[0] 
            with open(f, 'r') as lines:
                if f2 in self.special_filenames:
                    self.out_string += f2 + " = {\n"

                for line in lines:         
                    self.out_string += line

                if f2 in self.special_filenames:
                    self.out_string += "}"

            self.out_string += "\n"

        # ENV VARS
        for (k, v) in  os.environ.items():
            self.out_string = self.out_string.replace('${' + k + '}', v)






def main(argv=[]):

    epilog = """The following arguments can be activated using environment variables:

    export TG_DEBUG=y                   # activates debug messages
    export TG_APPLY=y                   # activates --force
    export TG_APPROVE=y                 # activates --force
    export TG_GIT_CHECK=y               # activates --git-check
    export TG_NO_GIT_CHECK=y            # activates --no-git-check
    export TG_MODULES_PATH              # required if using --dev

    """
    #TGARGS=("--force", "-f", "-y", "--yes", "--clean", "--dev", "--no-check-git")

    parser = argparse.ArgumentParser(description='TG, facilitates calling terragrunt with nifty features n such.', add_help=True, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    # subtle bug in ArgumentParser... nargs='?' doesn't work if you parse something other than sys.argv,
    parser.add_argument('command', default=None, nargs='*', help='terragrunt command to run (apply, destroy, plan, etc)')

    #parser.add_argument('--dev', default=None, help="if in dev mode, which dev module path to reference (TG_MODULES_PATH env var must be set and point to your local terragrunt repository path)")
    parser.add_argument('--downstream-args', default=None, help='optional arguments to pass downstream to terragrunt and terraform')

    # booleans
    parser.add_argument('--clean', dest='clean', action='store_true', help='clear all tg cache')
    parser.add_argument('--force', '--yes', '-t', '-f', action='store_true', help='Perform terragrunt action without asking for confirmation (same as --terragrunt-non-interactive)')
    parser.add_argument('--dry', action='store_true', help="dry run, don't actually do anything")
    parser.add_argument('--no-check-git', action='store_true', help='Explicitly skip git repository checks')
    parser.add_argument('--check-git', action='store_true', help='Explicitly enable git repository checks')
    parser.add_argument('--quiet', action='store_true', help='suppress output except fatal errors')

    clear_cache = False

    tp = TemplateParser()
    tp.parse()
    tp.save_outfile()

    exit
    args = parser.parse_args(args=argv)

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

    if args.check_git or os.getenv('TG_GIT_CHECK', 'n')[0].lower() in ['y', 't', '1']:
        CHECK_GIT = True

    if args.no_check_git or os.getenv('TG_NO_GIT_CHECK', 'n')[0].lower() in ['y', 't', '1'] :
        CHECK_GIT = False

    # check git
    if CHECK_GIT:
        gitstatus = git_check()
        if gitstatus != 0:
            return gitstatus

    try:
        WDIR = args.command[2]
    except:
        log("OOPS, no module directory specified, try one of these:")
        example_commands(command)
        return(100)





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


        TG_BIN = self.get_terragrunt_bin(WDIR)
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
                return self.TG_BIN

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