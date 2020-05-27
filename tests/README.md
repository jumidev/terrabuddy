# running terrabuddy tests

Terrabuddy tests use standard python unit test cases, to run them, simply do

```
make test
```

There is also a handy dockerfile at the root of this project that can be used to run the tests in docker.

```
docker build . -f Dockerfile-tests -t test-terrabuddy
docker run -it test-terrabuddy
```