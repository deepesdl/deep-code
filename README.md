# deep-code

[![Build Status](https://github.com/deepesdl/deep-code/actions/workflows/unittest-workflow.yaml/badge.svg)](https://github.com/deepesdl/deep-code/actions/workflows/unittest-workflow.yaml)
[![codecov](https://codecov.io/gh/deepesdl/deep-code/graph/badge.svg?token=47MQXOXWOK)](https://codecov.io/gh/deepesdl/deep-code)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/github/license/dcs4cop/xcube-smos)](https://github.com/deepesdl/deep-code/blob/main/LICENSE)

`deep-code` is a lightweight python tool that comprises a command line interface(CLI) 
and Python API providing utilities that aid integration of DeepESDL datasets, 
experiments with EarthCODE.

## Setup

## Install
`deep-code` will be available in PyPI and conda-forge. Till the stable release,
developers/contributors can follow the below steps to install deep-code.

## Installing from the repository for Developer

To install deep-code directly from the git repository, clone the repository, and execute the steps below:

```commandline
conda env create -f environment.yml
conda activate deep-code
pip install -e .
```

This installs all the dependencies of `deep-code` into a fresh conda environment, 
and installs deep-code from the repository into the same environment.

## Testing

To run the unit test suite:

```commandline
pytest
```

To analyze test coverage
```shell
pytest --cov=deep-code
```

To produce an HTML coverage report

```commandline
pytest --cov-report html --cov=deep-code
```

## deep_code usage

`deep_code` provides a command-line tool called deep-code, which has several subcommands 
providing different utility functions.
Use the --help option with these subcommands to get more details on usage.

###  deep-code publish-product

Publish a dataset which is a result of a experiment to the EarthCODE 
open-science catalog.

```commandline
 deep-code publish-product --help
 ```

```
Usage: deep-code publish-product [OPTIONS]

  Command-line interface for the ProductPublisher API.

Options:
  --git-config PATH      Path to the git.yaml file with GitHub credentials.
                         [required]
  --dataset-config PATH  Path to the dataset-config.yaml file with dataset
                         information.  [required]
  --help                 Show this message and exit.

```

#### git.yaml example

```
github-username: your-git-user
github-token: personal access token
```

#### dataset-config.yaml example

```
dataset-id: hydrology-1D-0.009deg-100x60x60-3.0.2.zarr 
collection-id: hydrology

#non-mandatory
documentation-link: https://deepesdl.readthedocs.io/en/latest/datasets/hydrology-1D-0-009deg-100x60x60-3-0-2-zarr/
access-link: s3://test
dataset-status: completed
dataset-region: global
dataset-theme: ["ocean", "environment"]
cf-parameter: [{"Name" : "hydrology"}]
```

dataset-id has to be a valid dataset-id from `deep-esdl-public` s3 or your team bucket.