# Configuration

## Dataset config (YAML)
```yaml
dataset_id: your-dataset.zarr
collection_id: your-collection
osc_themes: [cryosphere]
osc_region: global
dataset_status: completed   # or ongoing/planned
license_type: CC-BY-4.0
documentation_link: https://example.com/docs
access_link: s3://bucket/your-dataset.zarr

# Optional: publish a STAC Catalog + Item next to the data on S3.
# When set, a lightweight STAC hierarchy (catalog.json → item.json) is written
# directly to S3 and a "via" link is added to the OSC collection pointing to it.
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

S3 credentials are resolved in this order: `S3_USER_STORAGE_KEY` /
`S3_USER_STORAGE_SECRET` env vars, then `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY`, then the boto3 default chain (IAM role, `~/.aws/credentials`).

## Workflow config (YAML)
```yaml
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
jupyter_notebook_url: https://github.com/org/repo/path/to/notebook.ipynb
contact:
  - name: Jane Doe
    organization: Example Org
    links:
      - rel: about
        type: text/html
        href: https://example.org
```

More templates and examples live in `dataset_config.yaml`, `workflow_config.yaml`, and `example-config/`.
