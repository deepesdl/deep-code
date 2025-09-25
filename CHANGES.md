## Changes in 0.1.0

- Initial version of deep-code.
- Implemented the publish feature of DeepESDL experiments/workflow as OGC API record 
  and Datasets as an OSC stac collection.

## Changes in 0.1.1

- minor fix to fix nested quotes in f-string in dataset_stac_generator module.

## Changes in 0.1.2

- Support publishing to testing,staging and production repositories of 
  open-science-metadata.
- Implemented new cli command `generate-config` to generate starter templates for 
  config files.

## Changes in 0.1.3

- _Version bump only_; no code or functionality changes. This release was 
  republished to update the package on PyPI.

## Changes in 0.1.4

- Implemented custom rules using xrlint to validate metadata in dataset, which is necessary to 
  generate a STAC collection valid for ESA Open Science Catalog.
- Improved starter templates used for publishing.

## Changes in 0.1.5

- Automatic generation of git-pull redirect from a full GitHub notebook URL which 
  allows users to open the referenced book directly from DeepESDL.
- Introduced build_link_to_jnb method for creating STAC-compatible notebook links with 
  metadata on kernel, environment, and containerization.
- Added originating application platform metadata to generated OGC API records for 
  DeepESDL experiments and workflows.

## Changes in 0.1.6

- Publisher now supports `mode` parameter, This allows more flexible publishing:
  - `"dataset"` → publish dataset only
  - `"workflow"` → publish workflow only
  - `"all"` → publish both (default)

- CLI: publish now auto-detects dataset vs workflow configs and also accepts 
  --dataset-config / --workflow-config; single-file calls use -m to disambiguate 
  (e.g., deep-code publish workflow.yaml -m workflow).

- Contacts in OGC API records no longer include default or empty fields, only 
  properties explicitly defined in the workflow configuration will now be generated.