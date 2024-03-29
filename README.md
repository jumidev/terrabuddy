# terrabuddy

Terrabuddy is a templating engine built on top of [terraform](https://www.terraform.io/intro/index.html).  Terrabuddy allows terraform to be used in a way that is more **DRY**, more **auditable**, and more **modular.**

### Terrabuddy Features
- easily install and update terraform binaries
- easily manage component interdependencies via bundles 
- easily inject variables into your modules
- built in git workflow support


# Installation

### System Requirements

- python3 with pip3 in your $PATH
- `pip install terrabuddy`

**or install using setup.py**

```
git clone https://github.com/jumidev/terrabuddy.git
cd terrabuddy/tb
make install             # installs the tb CLI tool with python requirements

tb --setup               # downloads and installs terraform
tb --setup-terraformrc   # (optional) installs useful terraform default settings
tb --setup-shell         # (optional) installs useful tb shell aliases
```

### Installing & using terraform modules

terrabuddy can work with any terraform code.  

- A repo with modules for Azure is provided [here](https://github.com/jumidev/terraform-modules-azure.git)
- For AWS, [here](https://github.com/jumidev/terraform-modules-aws.git). (WIP)


# Background

`tb` is the terrabuddy command line interface.  It facilitates setting up your machine (see installation), allows you to list components and run terraform commands such as **plan**, **apply**, **destroy** and manages shared variables. 

tb introduces three notions for managing resoureces: **projects**, **components** and **bundles**.  A project is a git repo with a specific purpose.  Components are individual objects that you create on your cloud provider.  Bundles are sets of components that depend upon one another (and tb knows how to create them in the correct order).

## Anatomy of a project:

Below is an example project encompassing three environments

```
prep/
prod/
sbx/
.envrc.tpl
.gitignore
project.yml
README.md
tfstate_store.hclt
```

- The top level directories in the project correspond to the environments, `sbx` (sandbox), `prep` (pre-prod), and  `prod`.  
- .envrc.tpl contains a template for required environment variables, notably TF_MODULES_ROOT which points to the repo in to which terraform-modules-azure has been cloned
- project.yml contains project-specific variables.  Other .yml files within the project contain 
- tfstate_store.hclt is an hcl template that will be applied in all components

## Anatomy of a component:

Components are hclt files, e.g. hcl templates.  [HCL](https://www.terraform.io/docs/configuration/syntax.html) is a json-like declarative language used by terraform.

```
cat component.hclt

source  {
    # local path
    path = "/path/to/terraform/files"

    ....
    # OR a git repo
    repo = "https://github.com/jumidev/terraform-modules-aws.git"
}
inputs {
    foo = "bar"
}
```

- the `inputs` block contains the inputs which will be injected into the terraform module
- the `source` block tells tb which terraform module to use with this component, can be a local path or a git repo.
- hclt files contain variables, formatted `**${like_this}**`

### Component parsing and variables

When `tb` is run on a component, it:

1. lints/parses all hclt files, fails if there are syntax errors
1. loads all yml files in the component and all parent directories as variables. 
1. searches in the component directory and all parent directories for hclt files and combines them into a single hclt file. 
1. replaces all variables in the hclt.  If variables are left unreplaced, the parser stops with an error message.
1. if all variables are replaced, it performs the requested terraform action (`plan`, `apply`, `destroy`, etc)

**Component parsing in detail**

combines hclt files in the component directory with those in its parent directories.  For example, at the root of the project there is a tfstate_store.hclt file.  The contents of this file will be included in **all components**.

Another example is to refactor the source.hclt in a situation where a folder contains lots of components that use the same terraform module.

```
az-platform-infra$ ll prep/network_security_groups/*
prep/network_security_groups/bastion:
component.hclt

prep/network_security_groups/db:
component.hclt

prep/network_security_groups/db-apps:
component.hclt

prep/network_security_groups/public-webserver:
component.hclt
```

All of the above component.hclt contain the same `source` block  

We can add an hclt file with a `source` block in the top level folder, thusly:

```
az-platform-infra$ ll prep/network_security_groups/*

prep/network_security_groups:
source.hclt

prep/network_security_groups/bastion:
component.hclt

prep/network_security_groups/db:
component.hclt

prep/network_security_groups/db-apps:
component.hclt

prep/network_security_groups/public-webserver:
component.hclt
```

**Template Overriding**

hclt files in upper directoryies can be overriddden by placing files with the same name deeper in the filesystem.  For example, if you have a component that requires a specific tfstate_store configuration, you can override the one in the root folder, thusly:

```
prep/network_security_groups/public-webserver-other-remote-state:
component.hclt
tfstate_store.hclt  # overrides tfstate_store.hclt in project root
```

**Component variables in detail**

tb loads variables in a cascade process, starting at the project root and moving down the filesystem to the component.  For example for `prep/bastion/managed_disk`, the following yml files are loaded:

1. **project.yml** in the project root, contains various key/value pairs
1. **prep/env.yml** \
`env: "prep"`
1. **prep/bastion/appname.yml** \
`appname: "bastion"`

If, for example, **project.yml** contains `appname`, its value will be overridden by **prep/bastion/appname.yml**.

You can use tb to display component variables with the `showvars` command

```
$ tb showvars prep/bastion/managed_disk

COMPONENT_DIRNAME=managed_disk
COMPONENT_PATH=prep/bastion/managed_disk
PROJECT_ROOT=/home/user/myprojects/az-platform-infra
TB_INSTALL_PATH=/home/user/wf/terrabuddy/tb
appname=bastion
env=prep
location=westeurope
organization=wforg
private_subnet_cidr=172.16.4.0/22
project_name=platform-infra
public_subnet_cidr=172.16.2.0/24
vnet_cidr=172.16.0.0/19

```

**Special Variables**

In addition to variables loaded in .yml files, tb also provides special variables

- `COMPONENT_PATH` full path to component, relative to project
- `COMPONENT_DIRNAME` innermost component directory
- `PROJECT_ROOT` absolute path to project


## Bundles

Anywhere in a project, components can be bound together as a bundle, simply by placing a bundle.yml file with an `order` object.

For example, `prep/bastion/bundle.yml`

```
order:
    - network_interface
    - a_record
    - managed_disk
    - virtual_machine
```

The above bundle tells tb that when the user runs `tb <command> prep/bastion` it will in fact run four components: `prep/bastion/network_interface`, `prep/bastion/a_record`, etc... in the specified order.  When running the destroy command, this order is reversed.

You can use the `--dry` argument on a bundle to see its components:

```
$ tb show prep/bastion --dry

tb show prep/bastion/network_interface
tb show prep/bastion/a_record
tb show prep/bastion/managed_disk
tb show prep/bastion/virtual_machine
```

Bundles also support wildcards and other bundles, for example `prep/bundle.yml`

```
order:
    - resource_group
    - dns/zone/*                    # all components in this dir, alphabetical order
    - virtual_network
    - subnets/*                     # all components in this dir, alphabetical order
    - application_security_groups/* # all components in this dir, alphabetical order
    - network_security_groups/*     # all components in this dir, alphabetical order
    - bastion                       # this is another bundle
```

`tb <command> prep` is thus a single "monster" bundle that runs the entire prep environment


## Listing Components and bundles

tb uses the same commands as terraform: [plan, apply, destroy, refresh, etc](https://www.terraform.io/docs/commands/index.html).
Components in a project can be listed with the `tb plan|apply|show` command.

```
$ pwd
~/az-platform-infra
```

```
$ tb plan
OOPS, no component specified, try one of these (bundles are bold underlined):

tb plan sbx
tb plan sbx/application_security_groups/db-apps
tb plan sbx/application_security_groups/public-webserver
tb plan sbx/application_security_groups/manager
tb plan sbx/application_security_groups/db
tb plan sbx/application_security_groups/bastion
tb plan sbx/virtual_network
tb plan sbx/storage_account/std
tb plan sbx/storage_account/premium
tb plan sbx/dns/zone/sbx.weatherforce.net
tb plan sbx/dns/zone/sbx.prv
tb plan prod/keybaseca
tb plan prod/keybaseca/network_interface
tb plan prod/keybaseca/managed_disk
tb plan prod/keybaseca/virtual_machine
tb plan prod/keybaseca/a_record
tb plan prod/application_security_groups/db-apps
tb plan prod/application_security_groups/public-webserver
tb plan prod/application_security_groups/db
tb plan prod/bastion
tb plan prod/bastion/network_interface
tb plan prod/bastion/virtual_machine
tb plan prod/bastion/a_record
tb plan prod/resource_group
tb plan prod/network_security_groups/db-apps
tb plan prod/network_security_groups/public-webserver
tb plan prod/network_security_groups/db
...

```

## running `tb` commands

Each of the above lines is a component.  Running `tb plan <component>` will run the plan command on the component in question.

```
# TODO REDO
```

The above result means that the component already exists in Azure and is up to date with the component.

## Git workflow integration

`tb` was designed to take git workflow considerations into account.  When working with terrabuddy components, special care must be taken so ensure that developers working on separate components do not clobber each other's work.  tb includes git checking functions to inform developers if their local git repository is behind remote changes.

For instance, developers A and B work on two unrelated components.

1. Developer A is working on an application VM in `prep/testappA/virtual_machine`.  Developer A sees that network security rules do not allow their application to access required resources.  They amend the security group `prep/network_security_groups/db-apps` to add the required security rules.  They apply their changes and push to remote.
1. Developer B is working on an unrelated component.  They too need to amend `prep/network_security_groups/db-apps` to add their own required security rules (different from those that Developer A added).  They have forgotten to `git pull` so the changes made by Developer A are not on their machine.  **If they run `tb apply prep/network_security_groups/db-apps` they will clobber developer A's changes.**  
1. **However** tb does a git fetch and compares branches **before** each command.
1. Since Developer A has pushed their changes, tb on Developer B'a machine will show this message:
`GIT ERROR: You are on branch master and are behind the remote.  Please git pull and/or merge before proceeding.  Below is a git status:...`

The above also works for feature branches.  If developer B is working on a feature branch that was made prior to developer A's changes (pushed to master branch), tb will detect that Developer B's FB is behind master and prompt them to merge before proceeding.

# TODO

- remove terragrunt dependency
    - predictable temp dirs in home dir
    - auto cleanup previous runs older than x days
    - auto manage remote states, 
    - enrypted remote states
- tb catalog
    - for given resource type, get dependency tree, required and optional
- tb catalog-generator

- tb chart
    spin up a visualizer of current tb project
- example spoke and hub architecture
