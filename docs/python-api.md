# Python API

## LintDataset

`LintDataset` validates an xarray dataset against the metadata rules required for
publication to the ESA Open Science Catalog. Run it before publishing to catch
issues early.

```python
from deep_code.tools.lint import LintDataset

# Lint a Zarr dataset from the DeepESDL public/team bucket by ID
result = LintDataset(dataset_id="my-dataset.zarr").lint_dataset()

# Or lint an already-opened xarray.Dataset
import xarray as xr
ds = xr.open_zarr("s3://my-bucket/my-dataset.zarr")
result = LintDataset(dataset=ds).lint_dataset()

print(result)
```

### Validation rules

Two custom rules are checked:

| Rule | What is validated | If missing during publish |
|---|---|---|
| `deepcode/dataset-description` | Dataset has a `description` attribute in `ds.attrs`. | Falls back to `"No description available."` |
| `deepcode/variable-gcmd-keyword-url` | Every data variable has a `gcmd_keyword_url` attribute. | You are prompted to enter a URL for each affected variable interactively. |

Run `LintDataset` beforehand to spot metadata gaps before they interrupt the publish flow.

The same check is also available from the CLI — see [Lint a dataset](cli.md#lint-a-dataset).

---

## Publisher

`deep_code.tools.publish.Publisher` is the main entry point.

```python
from deep_code.tools.publish import Publisher

publisher = Publisher(
    dataset_config_path="dataset.yaml",
    workflow_config_path="workflow.yaml",
    environment="staging",  # "production" | "staging" | "testing"
)

# Generate files locally (no PR)
publisher.publish(write_to_file=True, mode="all")

# Or open a PR directly
publisher.publish(write_to_file=False, mode="dataset")
```

`mode` controls what is published:

| `mode` | What is published |
|---|---|
| `"dataset"` | OSC STAC collection, variable catalogs, product/variable base catalogs, project collection. |
| `"workflow"` | OGC API workflow and experiment records, workflow/experiment base catalogs. |
| `"all"` | Both of the above (default). |

---

## OscDatasetStacGenerator

`OscDatasetStacGenerator` can also be used directly when you need more control
over individual artifacts.

```python
from deep_code.utils.dataset_stac_generator import OscDatasetStacGenerator

generator = OscDatasetStacGenerator(
    dataset_id="my-dataset.zarr",
    collection_id="my-collection",
    workflow_id="my-workflow",
    workflow_title="My Workflow",
    license_type="CC-BY-4.0",
    osc_themes=["cryosphere"],
    osc_region="Global",
    osc_status="completed",
    # Optional: override the default project identifier.
    # Controls osc:project on the collection and the link to the project collection.
    osc_project="deep-earth-system-data-lab",
)
```

### `osc_project` parameter

`osc_project` defaults to `"deep-earth-system-data-lab"` and is used in three places:

1. Sets `osc:project` on the OSC extension of the generated STAC collection.
2. Generates the `related` link from the product collection to the project collection
   (`../../projects/{osc_project}/collection.json`).
3. Determines the file path of the project collection when publishing
   (`projects/{osc_project}/collection.json`).

### Automatic project collection creation

When `Publisher.publish_dataset()` runs, it checks whether
`projects/{osc_project}/collection.json` already exists in the catalog repository:

- **Missing** — a minimal STAC Collection is created for the project and a `child`
  link is appended to `projects/catalog.json` so it is reachable from the catalog root.
- **Exists** — the existing collection is updated with a `child` link to the new
  product and `related` links for its themes (same behaviour as before).

This means publishing to a new project does not require manual catalog setup.

### STAC Catalog and Item generation

```python
# Build the S3 STAC hierarchy (dict keyed by S3 path)
file_dict = generator.build_zarr_stac_catalog_file_dict(
    stac_catalog_s3_root="s3://bucket/stac/my-collection/"
)
# file_dict contains:
#   "s3://bucket/stac/my-collection/catalog.json"
#   "s3://bucket/stac/my-collection/my-collection/item.json"
```

See [STAC Catalog on S3](configuration.md#stac-catalog-on-s3) for details on the
generated structure.
