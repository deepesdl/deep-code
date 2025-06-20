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