# deep-code

[![Build Status](https://github.com/deepesdl/deep-code/actions/workflows/unittest-workflow.yaml/badge.svg)](https://github.com/deepesdl/deep-code/actions/workflows/unittest-workflow.yaml)
[![codecov](https://codecov.io/gh/deepesdl/deep-code/graph/badge.svg?token=47MQXOXWOK)](https://codecov.io/gh/deepesdl/deep-code)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/github/license/dcs4cop/xcube-smos)](https://github.com/deepesdl/deep-code/blob/main/LICENSE)

`deep-code` is a lightweight python tool that comprises a command line interface(CLI) 
and Python API providing utilities that aid integration of DeepESDL datasets, 
experiments with EarthCODE.

The first release will focus on implementing the publish feature of DeepESDL 
experiments/workflow as OGC API record and Datasets as an OSC stac collection.

## Setup

## Install
`deep-code` will be available in PyPI and conda-forge. Till the stable release,
developers/contributors can follow the below steps to install deep-code.

## Installing from the repository for Developers/Contributors

To install deep-code directly from the git repository, clone the repository, and execute the steps below:

```commandline
conda env create
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

The CLI retrieves the Git username and personal access token from a hidden file named .gitaccess. Ensure this file is located in the same directory where you execute the CLI
command.

###  deep-code publish-product

Publish a dataset which is a result of an experiment to the EarthCODE 
open-science catalog.

```commandline
 deep-code publish-dataset /path/to/dataset-config.yaml
 ```

#### .gitaccess example

```
github-username: your-git-user
github-token: personal access token
```

#### dataset-config.yaml example

```
dataset_id: hydrology-1D-0.009deg-100x60x60-3.0.2.zarr
collection_id: hydrology
osc_themes:
  - Land
  - Oceans
# non-mandatory
documentation_link: https://deepesdl.readthedocs.io/en/latest/datasets/hydrology-1D-0.009deg-100x60x60-3.0.2.zarr/
access_link: s3://test
dataset_status: completed
osc_region: global
cf_parameter:
  - name: hydrology
```

dataset-id has to be a valid dataset-id from `deep-esdl-public` s3 or your team bucket.

### deep-code publish-workflow

Publish a workflow/experiment to the EarthCODE open-science catalog.

```commandline
deep-code publish-workflow /path/to/workflow-config.yaml
 ```
#### workflow-config.yaml example

```
workflow_id: "4D Med hydrology cube generation"
properties:
  title: "Hydrology cube generation recipe"
  description: "4D Med cube generation"
  keywords:
    - Earth Science
  themes:
      - Atmosphere
      - Ocean
      - Evaporation
  license: proprietary
  jupyter_kernel_info:
    name: deepesdl-xcube-1.7.1
    python_version: 3.11
    env_file: https://git/env.yml
links:
  - rel: "documentation"
    type: "application/json"
    title: "4DMed Hydrology Cube Generation Recipe"
    href: "https://github.com/deepesdl/cube-gen/tree/main/hydrology/README.md"
  - rel: "jupyter-notebook"
    type: "application/json"
    title: "Workflow Jupyter Notebook"
    href: "https://github.com/deepesdl/cube-gen/blob/main/hydrology/notebooks/reading_hydrology.ipynb"
contact:
  - name: Tejas Morbagal Harish
    organization: Brockmann Consult GmbH
    links:
      - rel: "about"
        type: "text/html"
        href: "https://www.brockmann-consult.de/"
```
