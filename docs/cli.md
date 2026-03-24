# CLI

## Generate configs
Create starter templates for both workflow and dataset:

```bash
deep-code generate-config                 # writes to current directory
deep-code generate-config -o ./configs    # custom output folder
```

## Lint a dataset

Validate dataset metadata before publishing:

```bash
deep-code lint-dataset my-dataset.zarr
```

Checks that the dataset has all metadata required for a valid OSC STAC collection:

- `description` attribute present in `dataset.attrs` — if missing, publishing falls back to `"No description available."`
- `gcmd_keyword_url` attribute present on every data variable — if missing, publishing will prompt you to enter a URL for each affected variable interactively

Run this beforehand to spot and fix metadata gaps before they interrupt the publish flow.

## Publish metadata
Publish dataset, workflow, or both (default is both) to the target environment:

```bash
deep-code publish dataset.yaml workflow.yaml                 # production (default)
deep-code publish dataset.yaml workflow.yaml -e staging      # staging
deep-code publish dataset.yaml -m dataset                    # dataset only
deep-code publish workflow.yaml -m workflow                  # workflow only
deep-code publish --dataset-config ./ds.yaml --workflow-config ./wf.yaml -m all
```

Options:
- `--environment/-e`: `production` (default) | `staging` | `testing`
- `--mode/-m`: `all` (default) | `dataset` | `workflow`
- `--dataset-config` / `--workflow-config`: explicitly set paths and bypass auto-detection

## How publishing works
1. Reads your configs and builds dataset STAC collections plus variable catalogs.
2. Builds workflow and experiment OGC API Records.
3. Forks/clones the target metadata repo (production, staging, or testing), commits generated JSON, and opens a pull request on your behalf.

The pull request description includes a "Generated with deep-code" attribution note.
