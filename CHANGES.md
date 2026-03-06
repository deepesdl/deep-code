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

## Changes in 0.1.8 (in Development)

- Fixed a crash in workflow publishing when `jupyter_notebook_url` is not provided in
  the workflow config. `jupyter_kernel_info`, `application_link`, and `jnb_open_link`
  are now only computed when a notebook URL is present, making the field truly optional.

- Added STAC Item and S3-hosted STAC Catalog generation for Zarr datasets, enabling
  a richer `STAC Collection → STAC Catalog (S3) → STAC Item` hierarchy alongside the
  existing OSC metadata.
  - A single STAC Item is generated per Zarr store, covering the full spatiotemporal
    extent with two assets: `zarr-data` (`application/vnd+zarr`) and
    `zarr-consolidated-metadata` (`.zmetadata`).
  - The S3 STAC catalog and item are written directly to S3 via `fsspec`/`s3fs`
    independently of the GitHub PR.
  - The OSC STAC Collection gains a `child` link pointing to the S3 catalog root,
    connecting the two levels of the hierarchy.
  - Opt-in via the new `stac_catalog_s3_root` field in `dataset_config.yaml`
    (e.g. `stac_catalog_s3_root: s3://my-bucket/stac/my-collection/`).
  - S3 write credentials are resolved from `S3_USER_STORAGE_KEY`/`S3_USER_STORAGE_SECRET`,
    `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, or the boto3 default chain
    (IAM role, `~/.aws/credentials`) — no secrets in config files.
