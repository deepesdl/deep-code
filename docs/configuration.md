# Configuration

The quickest way to get started is to generate starter templates with the CLI:

```bash
deep-code generate-config              # writes to current directory
deep-code generate-config -o ./configs # custom output folder
```

This creates `dataset_config.yaml` and `workflow_config.yaml` with all supported fields and placeholder values. Fill them in, then run [`deep-code publish`](cli.md#publish-metadata).

The sections below document every field in those templates.

---

## Dataset config (YAML)
```yaml
# Required
dataset_id: your-dataset.zarr
collection_id: your-collection       # no spaces — use hyphens
license_type: CC-BY-4.0
stac_catalog_s3_root: s3://bucket/stac/your-collection/

# Optional
osc_themes: [cryosphere]        # must match slugs at opensciencedata.esa.int/themes/catalog — auto-lowercased
osc_region: global
dataset_status: completed       # ongoing | completed | planned (default: ongoing)
documentation_link: https://example.com/docs
visualisation_link: https://example.com/viewer   # URL to a visualisation of the dataset
osc_project: deep-earth-system-data-lab          # defaults to deep-earth-system-data-lab
access_link: s3://bucket/your-dataset.zarr   # defaults to s3://deep-esdl-public/{dataset_id}

# CF parameter overrides (list of {name, units, ...} dicts)
cf_parameter:
  - name: sea_surface_temperature
    units: kelvin
```

### Field reference

| Field | Required | Description |
|---|---|---|
| `dataset_id` | Yes | Zarr store identifier (used to open the dataset). |
| `collection_id` | Yes | Unique ID for the STAC collection in the OSC catalog. **Must not contain spaces** — use hyphens as word separators (e.g. `My-Dataset-2024`). |
| `license_type` | Yes | SPDX license identifier (e.g. `CC-BY-4.0`). Publishing fails if this field is absent. |
| `osc_themes` | No | List of OSC theme slugs (e.g. `[cryosphere, oceans]`). Values are automatically lowercased so `Land` and `land` are equivalent. |
| `osc_region` | No | Geographical region label (default: `Global`). |
| `dataset_status` | No | One of `ongoing`, `completed`, or `planned` (default: `ongoing`). |
| `access_link` | No | Public S3 URL of the Zarr store. Defaults to `s3://deep-esdl-public/{dataset_id}`. |
| `description` | No | Human-readable description of the dataset. Overrides the `description` attribute in the Zarr store; falls back to `"No description available."` if neither is set. |
| `documentation_link` | No | URL to dataset documentation. |
| `visualisation_link` | No | URL to a visualisation of the dataset (e.g. xcube Viewer, WMS). Added as a `visualisation` link with title `"Dataset visualisation"`. |
| `osc_project` | No | OSC project ID this dataset belongs to (e.g. `deep-earth-system-data-lab`). Defaults to `deep-earth-system-data-lab`. |
| `cf_parameter` | No | List of CF metadata dicts to override variable attributes (e.g. `name`, `units`). |
| `stac_catalog_s3_root` | Yes | S3 root where the STAC Catalog and Item are published. Publishing fails if this field is absent. See [STAC Catalog on S3](#stac-catalog-on-s3). |

### STAC Catalog on S3

`stac_catalog_s3_root` is required. deep-code writes a two-file STAC hierarchy to S3 alongside the data:

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
  # jupyter_kernel_info is optional — only published when jupyter_notebook_url is set
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
| `properties.license` | Yes | SPDX license identifier (e.g. `CC-BY-4.0`, `proprietary`). Publishing fails if this field is absent. |
| `jupyter_notebook_url` | No | Link to the source notebook on GitHub. When omitted, kernel and application links are skipped. |
| `properties.jupyter_kernel_info` | No | Kernel name, Python version, and environment file URL. Only published when `jupyter_notebook_url` is set. |
| `contact` | No | List of contact objects with `name`, `organization`, and `links`. |
| `links` | No | Additional OGC API record links (e.g. `related`, `describedby`). |

More templates and examples live in `dataset_config.yaml`, `workflow_config.yaml`, and `example-config/`.
