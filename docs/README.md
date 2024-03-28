# Getting started

- [Why Cloudicorn](#why-cloudicorn)
- [Installation](installation.md)
- [Core Concepts](#core-concepts)
- Examples

## Why Cloudicorn

In many cases, terraform (and infra as code as a whole) is the ugly duckling in a company's codebase. Implementing new features usually takes priority over IAC because that is what adds value. As infrastructure requirements change, developers will often implement them manually, or if forced to code them, will lump terraform code into monoliths, running the code over and over and over until it works and calling it a day. Infra as code is thusly often neglected and quietly accumulates technical debt. 

Cloudicorn was created to be a pragmatic solution to these common problems with the aim of turning IAC codebase into be a critical asset.

## Core Concepts

Cloudicorn is built on top of terraform.  terraform serves as a good foundation for IAC due to its maturity and rich functionalities.  However, writing terraform code, maintaining configuration and running terraform involves a lot of complexity and requires specific skill sets.  Cloudicorn serves to encapsulate this underlying complexity as much as possible while providing added value.  

For more information, see the dedicated [core concepts](core_concepts.md) page.

## Examples


```TODO```