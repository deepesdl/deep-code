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
`deep-code` will be available in PyPI for now and will be available in conda-forge 
in the near future. Till the stable release,
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

The CLI retrieves the Git username and personal access token from a hidden file named 
.gitaccess. Ensure this file is located in the same directory where you execute the CLI
command.

#### .gitaccess example

```
github-username: your-git-user
github-token: personal access token
```
### deep-code generate-config

Generates starter configuration templates for publishing to EarthCODE openscience 
catalog.

#### Usage
```
deep-code generate-config [OPTIONS]
```

#### Options
     --output-dir, -o : Output directory (default: current)

#### Examples:
```
deep-code generate-config
deep-code generate-config -o ./configs
```

###  deep-code publish

Publishes metadata of experiment, workflow and dataset to the EarthCODE open-science 
catalog

### Usage
```
deep-code publish DATASET_CONFIG WORKFLOW_CONFIG [--environment ENVIRONMENT] [--mode 
all|dataset|workflow]
 ```

#### Arguments
    DATASET_CONFIG - Path to the dataset configuration YAML file
    (e.g., dataset-config.yaml)

    WORKFLOW_CONFIG - Path to the workflow configuration YAML file
    (e.g., workflow-config.yaml)

#### Options
    --dataset-config, - Explict path to dataset config
    --workflow-config, - Explicit path to workflow config
    --environment, -e - Target catalog environment:
    production (default) | staging | testing
    --mode, -m Publishing mode:
    all (default) | dataset | workflow

#### Examples:
1. Publish to staging catalog
```
deep-code publish dataset-config.yaml workflow-config.yaml --environment=staging
```
2. Publish to testing catalog
```
deep-code publish dataset-config.yaml workflow-config.yaml -e testing
```
3. Publish to production catalog
```
deep-code publish dataset-config.yaml workflow-config.yaml
```
4. Publish Dataset only
```
deep-code publish dataset-config.yaml -m dataset

deep-code publish --dataset-config dataset.yaml -m dataset
```
5. Publish Workflow only
```
deep-code publish dataset-config.yaml -m workflow

deep-code publish --workflow-config workflow.yaml -m dataset
```
#### dataset-config.yaml example

```
dataset_id: esa-cci-permafrost-1x1151x1641-1.0.0.zarr
collection_id: esa-cci-permafrost
osc_themes:
  - cryosphere
osc_region: global
# non-mandatory
documentation_link: https://deepesdl.readthedocs.io/en/latest/datasets/esa-cci-permafrost-1x1151x1641-0-0-2-zarr
access_link: s3://deep-esdl-public/esa-cci-permafrost-1x1151x1641-1.0.0.zarr
dataset_status: completed
```

dataset-id has to be a valid dataset-id from `deep-esdl-public` s3 bucket or your team 
bucket.

#### workflow-config.yaml example

```
workflow_id: "esa-cci-permafrost"
properties:
  title: "ESA CCI permafrost"
  description: "cube generation workflow for esa-cci-permafrost"
  keywords:
    - Earth Science
  themes:
      - cryosphere
  license: proprietary
  jupyter_kernel_info:
    name: deepesdl-xcube-1.8.3
    python_version: 3.11
    env_file: "https://github.com/deepesdl/cube-gen/blob/main/Permafrost/environment.yml"
jupyter_notebook_url: "https://github.com/deepesdl/cube-gen/blob/main/Permafrost/Create-CCI-Permafrost-cube-EarthCODE.ipynb"
contact:
  - name: Tejas Morbagal Harish
    organization: Brockmann Consult GmbH
    links:
      - rel: "about"
        type: "text/html"
        href: "https://www.brockmann-consult.de/"
```
