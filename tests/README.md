# running terrabuddy tests

Terrabuddy tests use standard python unit test cases, to run them, simply do

```
make test
```

There is also a dockerfile at the root of this project that can be used to run the tests in docker.

```
docker build . -f Dockerfile-tests -t test-terrabuddy
docker run -it test-terrabuddy
```

# TODO
- ~~test componentsource git tag~~
- ~~test tfsource git tag wildcards~~
- ~~test vars.yml variables~~
- ~~test creating multiple vpc subnets using map and tfstate link~~
- tb_setup
   - ~~init project~~
   - ~~setup s3 tfstate store~~
   - ~~setup azure creds~~
   - ~~setup azure tfstate store~~
   - ~~setup tfstate encryption~~
   - ~~setup linked project(s)~~
   - ~~setup multiple encryption keys~~
- ~~test hcl dumping -> strings, lists, maps, recursively~~
- ~~test fetching value(s) from tfstates~~
- ~~test copy all files from component dir to tfdir (for ex tf overrides)~~
- test azurerm
   - ~~rg and tfstate~~
- test aws bundle
- test list type tfstate_inputs
- test dict type tfstate_inputs
- linked projects
   - ~~path~~
   - ~~git~~
   - failure modes:
      - not all vars replaced
      - ~~no tfstate~~
      - ~~no such branch~~
- ~~clean azure storage tests, delete all tfstates~~
- tfstate_inputs, add support for blocks.
      e.g. in network_security_group, inputs
      
- add exitcodes in custom exceptions intbcore, catch them in tb
- test tb showvars
- test tb --key
- tb support all arguments in env var format
- test tb shell
- test aws sts auth
- test azure auth
- test various env vars options
- test git workflow
- test apply failure modes:
  - no resources created, tfstate still uploaded
  - some, but not add resources created, tfstate still uploaded
  - second apply attempt with problem fixed, previously created resources not recreated
