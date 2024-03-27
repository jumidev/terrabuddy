Cloud infrastructure is **Difficult**, **Messy** and **Volatile.**

Difficult because it requires a broad spectrum of skills from systems, to programming to networking and troubleshooting \
Messy because infrastructure has to reckon with multiple, often conflicting constraints.  Technical constraints, cost constraints, regulatory and vendor constraints, client imposed constraints, you get the idea.\
Volatile because technology is always changing.  Because small infrastructure changes can have big impacts.

Managing infrastructure should add as little additional difficulty as possible, make the mess more navigable (rather than adding more mess) and make the volatility of infrastructure as manageable as possible


# Cloudicorn + Terraform = 😎

Cloudicorn is what infra as code should be.  It's a combination of terraform with a specific methodolgy and toolset to make IAC easy to bootstrap, scalable, and resistant to technical debt

### Terraform in a nutshell

Terraform is a powerful and mature tool for implementing your cloud infrastructure as code. Its major features are:
- **easy to read code** infrastructure code is in a human readable, easy to audit format
- **extendable** support for all cloud platforms (aws, azure, gcp, etc...) via provider plugins
- **mature** best in class documentation, large user community, stable codebase and stable plugins
- **stage changes before deploying** terraform plans and displays changes before applying them to avoid surprises
- **idempotence** code can be several times without changing the final result, so easy to put into CICD pipelines

### However...

In many cases, terraform (and infra as code as a whole) is the ugly duckling in your codebase. Implementing new features and adding value to applications usually takes priority over IAC.  As infrastructure requirements change, developers will often implement them manually, or if forced to code them, will lump terraform code into monoliths, running the code over and over and over until it works and returning to more pressing issues.  Infra as code is thus often neglected and quietly accumulates technical debt.  Luckily, with the right tools and methods, IAC has the potential to be a critical asset.

# What IAC Should Be

- **Infrastructure is never perfect.**  There are always special cases, cost / benefit compromises, legacy systems, temporary workarounds, long migrations and surprises.  IAC should not get in the of way implementing these specificities, rather it should enable colleagues to document them clearly, easily understand how the pieces fit together, and have a clear vision of future changes.
- Infra as code **should be simple**.  It should take as little developer time as possible while being accessible to other stakeholders such as architects, support, cyber security and monitoring teams.
- Infra as code **should be visual and auditable**.  Humanity has had maps for centuries, IAC should be the always up to date map of your infrastrucure.

# The cloudicorn approach

- Using Cloudicorn, cloud assets are grouped into functional units called `components.`  Unlike terraform resources whose interdependencies are **technical**, components are **functional**
- Cloudicorn ships with pre-coded components for major cloud providers designed to fit most use cases.  You can of course write your own components!
- Cloudicorn provides a gui tool to visualize your infrastructure from a functional point of view.

