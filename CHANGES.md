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

- CLI: the `publish` command now auto-detects dataset vs workflow configs and also accepts 
  --dataset-config / --workflow-config; single-file calls use -m to disambiguate 
  (e.g., deep-code publish workflow.yaml -m workflow).

- Contacts in OGC API records no longer include default or empty fields, only 
  properties explicitly defined in the workflow configuration will now be generated.

- Enhanced GitHub automation to automatically fork synchronize with upstream before 
  committing and opening a PR to ensure branches are always up-to-date.

- Prevented duplicate item and self links when updating base catalogs of workflows and 
  experiments.

## Changes in 0.1.7

- Fixed a bug in build_child_link_to_related_experiment for the publish mode `"all"`.

## Changes in 0.1.8

- Fixed a crash in workflow publishing when `jupyter_notebook_url` is absent in the config.
- Added STAC Item and S3-hosted STAC Catalog generation for Zarr datasets (opt-in via `stac_catalog_s3_root` in dataset config).
- `osc_project` is now a configurable parameter on `OscDatasetStacGenerator` (default: `"deep-earth-system-data-lab"`).
- Publisher automatically creates the OSC project collection and registers it in `projects/catalog.json` when it does not yet exist.

## Changes in 0.1.9

- `jupyter_kernel_info` is now optional in `RecordProperties`; workflow configs without a notebook URL no longer require this field.
- Removed redundant `hasattr` guard for `_last_generator` in `Publisher.publish()`.
- Added automated MkDocs GitHub Pages deployment on release via a dedicated `docs.yml` workflow.
- `osc_themes` values are now automatically lowercased, so `'Land'` and `'LAND'` are treated the same as `'land'`, preventing theme validation failures.
- `collection_id` is now validated to contain no spaces; a clear error is raised with a hint to use hyphens instead.
- `license_type` (dataset) and `properties.license` (workflow) are now mandatory fields; publishing fails immediately with a descriptive error if either is missing.
- Variable catalog `description` now falls back to the title-cased variable ID when neither `description` nor `long_name` attrs are present on the zarr variable, preventing `null` description validation failures.
- Pull requests opened by deep-code now include a "Generated with deep-code" note in the PR description.
- `stac_catalog_s3_root` is now a mandatory field in the dataset config; publishing fails immediately with a descriptive error if it is absent.
- STAC catalog links in the OSC collection now follow the OSC convention: a `via` link to the STAC browser URL and a `child` link to the direct HTTPS catalog URL. The `s3://` URL is converted to HTTPS (AWS virtual-hosted style) to satisfy the `uri-reference` format check in the OSC products schema.
- Added optional `visualisation_link` field to the dataset config; when provided, a `visualisation` link with title `"Dataset visualisation"` is added to the generated OSC collection.
- Added optional `description` field to the dataset config; overrides the `description` attribute from the Zarr store when set.
- Added optional `osc_project_title` field to the dataset config to correctly set the project link title (e.g. `"DeepESDL"`) instead of deriving it from the project ID.
- Fixed `workflow_id` not being normalised (slugified) when stored on `Publisher`, causing spaces in experiment link hrefs and failing `uri-reference` format validation.
- Removed redundant `via` access link from the OSC STAC collection; access is already expressed via typed assets (`zarr-data`, `zarr-consolidated-metadata`) on the STAC item.
- `osc_project` is now omitted from `OscDatasetStacGenerator` when not provided, preserving the callee's default instead of passing `None`.
