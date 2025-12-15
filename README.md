# deep-code

[![Build Status](https://github.com/deepesdl/deep-code/actions/workflows/unittest-workflow.yaml/badge.svg)](https://github.com/deepesdl/deep-code/actions/workflows/unittest-workflow.yaml)
[![codecov](https://codecov.io/gh/deepesdl/deep-code/graph/badge.svg?token=47MQXOXWOK)](https://codecov.io/gh/deepesdl/deep-code)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/github/license/dcs4cop/xcube-smos)](https://github.com/deepesdl/deep-code/blob/main/LICENSE)

`deep-code` is a lightweight Python CLI and API that turns DeepESDL datasets and 
workflows into EarthCODE Open Science Catalog metadata. It can generate starter configs,
build STAC collections and OGC API records, and open pull requests to the target 
EarthCODE metadata repository (production, staging, or testing).

## Features
- Generate starter dataset and workflow YAML templates.
- Publish dataset collections, workflows, and experiments via a single command.
- Build STAC collections and catalogs for Datasets and their corresponding variables 
  automatically from the dataset metadata.
- Build OGC API records for Workflows and Experiments from your configs.
- Flexible publishling targets i.e production/staging/testing EarthCODE metadata 
  repositories with GitHub automation.
