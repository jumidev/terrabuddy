#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json, os, sys,  hcl, shutil, time
import argparse
from pyfiglet import Figlet
import datetime
import hashlib
from pathlib import Path
import time
import tbcore
from tbcore import Utils, Project, run, runshow, WrapTerraform, log, debug, flatwalk, git_check, delfiles, RemoteStateReader
from tbcore import ComponentSourceGit, ComponentSourcePath
from tbcore import TfStateStoreAwsS3, TfStateStoreAzureStorage, TfStateStoreFilesystem

PACKAGE = "tb"
LOG = True
DEBUG=False

def main(argv=[]):

    epilog = """The following arguments can be activated using environment variables:

    export TB_DEBUG=y                   # activates debug messages
    export TB_APPROVE=y                 # activates --yes
    export TB_GIT_CHECK=y               # activates --git-check
    export TB_NO_GIT_CHECK=y            # activates --no-git-check
    export TB_MODULES_PATH              # required if using --dev
    export TB_GIT_FILTER                # when displaying components, only show those which have uncomitted git files
    export TB_TFSTATE_STORE_ENCRYPTION_PASSPHRASE #if set, passphrase to encrypt and decrypt remote state files at rest
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
    parser.add_argument('--allow-no-tfstate-store', action='store_true', help="allow components to be run without a tfstate_store block")
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
    tfstate_store_encryption_passphrase = os.getenv("TB_TFSTATE_STORE_ENCRYPTION_PASSPHRASE", None)
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

            check = project.check_parsed_file(require_tfstate_store_block=not args.allow_no_tfstate_store)
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

                    tfstate_file = "{}/terraform.tfstate".format(tf_wdir)

                    if "tfstate_store" in obj:
                        # instanciate TfStateStore
                        if "bucket" in obj["tfstate_store"]:
                            crs = TfStateStoreAwsS3(args=obj["tfstate_store"], localpath=tfstate_file)
                        elif "storage_account" in obj["tfstate_store"]:
                            crs = TfStateStoreAzureStorage(args=obj["tfstate_store"], localpath=tfstate_file)
                        elif "path" in obj["tfstate_store"]:
                            crs = TfStateStoreFilesystem(args=obj["tfstate_store"], localpath=tfstate_file)
                        else:
                            raise Exception("No TfStateStore handler for component")

                        crs.fetch()

                        if crs.is_encrypted:
                            if tfstate_store_encryption_passphrase == None:
                                raise tbcore.MissingEncryptionPassphrase("Remote state for component is encrypted, you must provide a decryption passphrase")
                            crs.set_passphrase(tfstate_store_encryption_passphrase)
                            crs.decrypt()

                    else:
                        # touch tfstate
                        Path(tfstate_file).touch()

                    # extract inputs into tfvars
                    with open("{}/terraform.tfvars".format(tf_wdir), "w") as fh:
                        for k,v in obj["inputs"].items():
                            fh.write("{} = \"{}\"".format(k,v.replace('"', '\\"')))
                            fh.write("\n")

                    # terraform init
                    cmd =  "{} init ".format(wt.tf_bin)
                    
                    exitcode = runshow(cmd, cwd=tf_wdir)
                    if exitcode != 0:
                        raise tbcore.TerraformException("\ndir={}\ncmd={}".format(tf_wdir, cmd))
                                        
                    # requested command
                    extra_args = ['-state=terraform.tfstate']

                    cmd = wt.get_command(command, extra_args)

                    exitcode = runshow(cmd, cwd=tf_wdir)
                    if exitcode != 0:
                        raise tbcore.TerraformException("\ndir={}\ncmd={}".format(tf_wdir, cmd))

                    # our work is done here
                    if command in ["refresh", "plan"]:
                        return 0

                    # # terraform apply
                    # cmd =  "{} apply -state=terraform.tfstate tfplan".format(wt.tf_bin)
                    # exitcode = runshow(cmd, cwd=tf_wdir)
                    # if exitcode != 0:
                    #     raise TerraformException("\ndir={}\ncmd={}".format(tf_wdir, cmd))
                    
                    if tfstate_store_encryption_passphrase != None:
                        crs.set_passphrase(tfstate_store_encryption_passphrase)
                        crs.encrypt()

                    # save tfstate
                    crs.push()
                    return 0

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
