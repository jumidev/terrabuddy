# Here's the deal:

Managing Cloud infrastructure is **`Difficult`**, **`Messy`** and **`Volatile.`**

**`Difficult`** because it requires a broad spectrum of skills ranging from programming to systems to networking and troubleshooting. \
**`Messy`** because infrastructure has to reconcile multiple, sometimes conflicting constraints.  Technical constraints, cost constraints, regulatory and vendor constraints, security constraints, client-imposed constraints.... you get the idea.\
**`Volatile`**  Because your infrastructure is always growing.  Because small infrastructure changes can sometimes have unexpected impacts.

# What IAC Should Be

- **Your infrastructure is never perfect.**  There are always special cases, cost / benefit compromises, legacy systems, temporary workarounds, long migrations and surprises.  IAC should not get in the of way implementing these specificities, rather it should enable colleagues with all skillsets to document them clearly, easily understand how the pieces fit together, and have a clear vision of future changes.
- Infra as code **should be simple**.  It should not add unneccessary burden to developers, it should be accessible to other stakeholders such as architects, support, cyber security and monitoring teams.
- Infra as code **should be visual and auditable**.  Humanity has had maps for centuries, IAC should be the always up to date map of your infrastrucure.

# The cloudicorn approach

- Using Cloudicorn, cloud assets are grouped into functional units called `components.`  Unlike terraform resources whose interdependencies are **technical**, components are **functional**.  Anyone with a basic understanding of cloud assets can understand what a component is without having to master the technical specifics.
- Cloudicorn ships with pre-coded components for major cloud providers designed to fit most use cases.  You can of course write your own components!
- Cloudicorn provides a web interface to visualize your infrastructure from a meaningful functional point of view.

There's more to it than that, but that's the idea.  Thanks for making it this far.  If you're interested in learning more about cloudicorn:

- Getting Started
- Installation
- Core concepts
- Examples

