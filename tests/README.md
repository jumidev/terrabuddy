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

test componentsource tags
test vars.yml variables
test creating multiple vpc subnets using map and rskey
test rskeys
test fetching value(s) from tfstates

test azurerm

test aws bundle
test tb shell
test aws sts auth
test azure auth

test various env vars options
test git workflow