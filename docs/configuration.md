# Configuration

## Dataset config (YAML)
```yaml
# Required
dataset_id: your-dataset.zarr
collection_id: your-collection
license_type: CC-BY-4.0

# Optional
osc_themes: [cryosphere]        # must match slugs at opensciencedata.esa.int/themes/catalog
osc_region: global
dataset_status: completed       # ongoing | completed | planned (default: ongoing)
documentation_link: https://example.com/docs
access_link: s3://bucket/your-dataset.zarr   # defaults to s3://deep-esdl-public/{dataset_id}

# CF parameter overrides (list of {name, units, ...} dicts)
cf_parameter:
  - name: sea_surface_temperature
    units: kelvin

# Optional: publish a STAC Catalog + Item next to the data on S3.
# When set, a lightweight STAC hierarchy (catalog.json → item.json) is written
# directly to S3 and a "via" link is added to the OSC collection pointing to it.
# S3 write credentials are resolved in order:
#   1. STAC_S3_KEY / STAC_S3_SECRET  (STAC-specific, any bucket)
#   2. AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
#   3. boto3 default chain (IAM role, ~/.aws/credentials)
stac_catalog_s3_root: s3://bucket/stac/your-collection/
```

### Field reference

| Field | Required | Description |
|---|---|---|
| `dataset_id` | Yes | Zarr store identifier (used to open the dataset). |
| `collection_id` | Yes | Unique ID for the STAC collection in the OSC catalog. |
| `license_type` | Yes | SPDX license identifier (e.g. `CC-BY-4.0`). |
| `osc_themes` | No | List of OSC theme slugs (e.g. `[cryosphere, oceans]`). |
| `osc_region` | No | Geographical region label (default: `Global`). |
| `dataset_status` | No | One of `ongoing`, `completed`, or `planned` (default: `ongoing`). |
| `access_link` | No | Public S3 URL of the Zarr store. Defaults to `s3://deep-esdl-public/{dataset_id}`. |
| `documentation_link` | No | URL to dataset documentation. |
| `cf_parameter` | No | List of CF metadata dicts to override variable attributes (e.g. `name`, `units`). |
| `stac_catalog_s3_root` | No | S3 root for the dataset-level STAC Catalog/Item. See [STAC Catalog on S3](#stac-catalog-on-s3). |

### STAC Catalog on S3

Setting `stac_catalog_s3_root` generates a two-file STAC hierarchy on S3 alongside
the data:

```
s3://bucket/stac/your-collection/
├── catalog.json        # STAC Catalog (root)
└── your-collection/
    └── item.json       # STAC Item covering the full Zarr store
```

The item has two assets:

- `zarr-data` — points to the Zarr store (`application/vnd+zarr`).
- `zarr-consolidated-metadata` — points to `.zmetadata` (`application/json`).

The OSC collection gains a `via` link to `catalog.json` so STAC-aware clients
can discover the data path. `rel="child"` is intentionally avoided because the
OSC validator requires every `child` link to resolve inside the metadata repository.

S3 credentials for writing the STAC catalog are resolved in this order:
`STAC_S3_KEY` / `STAC_S3_SECRET` env vars (STAC-specific, can target any bucket),
then `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`,
then the boto3 default chain (IAM role, `~/.aws/credentials`).

## Workflow config (YAML)
```yaml
# Required
workflow_id: your-workflow
properties:
  title: "My workflow"
  description: "What this workflow does"
  keywords: ["Earth Science"]
  themes: ["cryosphere"]
  license: proprietary
  jupyter_kernel_info:
    name: deepesdl-xcube-1.8.3
    python_version: 3.11
    env_file: https://example.com/environment.yml

# Optional
jupyter_notebook_url: https://github.com/org/repo/path/to/notebook.ipynb
contact:
  - name: Jane Doe
    organization: Example Org
    links:
      - rel: about
        type: text/html
        href: https://example.org
links:
  - rel: related
    type: text/html
    href: https://example.com/related-resource
    title: Related resource
```

### Field reference

| Field | Required | Description |
|---|---|---|
| `workflow_id` | Yes | Unique identifier for the workflow (spaces converted to hyphens, lowercased). |
| `properties.title` | Yes | Human-readable title. |
| `properties.description` | No | Short summary of what the workflow does. |
| `properties.keywords` | No | List of keyword strings. |
| `properties.themes` | No | List of OSC theme slugs. |
| `properties.license` | No | License identifier (e.g. `proprietary`, `CC-BY-4.0`). |
| `properties.jupyter_kernel_info` | No | Kernel name, Python version, and environment file URL. |
| `jupyter_notebook_url` | No | Link to the source notebook on GitHub. When omitted, kernel and application links are skipped. |
| `contact` | No | List of contact objects with `name`, `organization`, and `links`. |
| `links` | No | Additional OGC API record links (e.g. `related`, `describedby`). |

More templates and examples live in `dataset_config.yaml`, `workflow_config.yaml`, and `example-config/`.
