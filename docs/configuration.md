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
collection_id: your-collection       # no spaces — use hyphens
license_type: CC-BY-4.0
stac_catalog_s3_root: s3://bucket/stac/your-collection/
items_config:
  - dataset_id: your-dataset.zarr
    item_id: your-item               # no spaces — use hyphens

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

# PRR fields (only used by `deep-code generate-prr-collection`)
osc_initiative: earthcode                     # earthcode | apex (default: earthcode)
osc_missions: [sentinel-3]
osc_contract_number: 4000114410/15/NL/BW
osc_project_website: https://project.example.org
osc_project_description: A detailed multi-line description of the project.
thumbnail: https://example.org/thumbnail.jpeg
sci_doi: 10.1000/xyz123
prr_output_dir: ./prr/your-collection
```

### Field reference

| Field                  | Required | Description                                                                                                                                                        |
|------------------------|---|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `collection_id`        | Yes | Unique ID for the STAC collection in the OSC catalog. **Must not contain spaces** — use hyphens as word separators (e.g. `My-Collection-2024`).                    |
| `license_type`         | Yes | SPDX license identifier (e.g. `CC-BY-4.0`). Publishing fails if this field is absent.                                                                              |
| `items_config`         | Yes | List of `{dataset_id, item_id}` entries. Use one entry for `publish` today; the generator can emit multiple items when more are provided.                          |
| `dataset_id`           | Legacy | Single-item fallback when `items_config` is omitted.                                                                                                               |
| `item_id`              | Legacy | Single-item fallback when `items_config` is omitted. If omitted there, deep-code falls back to the `collection_id` for compatibility.                              |
| `osc_themes`           | No | List of OSC theme slugs (e.g. `[cryosphere, oceans]`). Values are automatically lowercased so `Land` and `land` are equivalent.                                    |
| `osc_region`           | No | Geographical region label (default: `Global`).                                                                                                                     |
| `dataset_status`       | No | One of `ongoing`, `completed`, or `planned` (default: `ongoing`).                                                                                                  |
| `access_link`          | No | Public S3 URL of the Zarr store. Defaults to `s3://deep-esdl-public/{dataset_id}`.                                                                                 |
| `description`          | No | Human-readable description of the dataset. Overrides the `description` attribute in the Zarr store; falls back to `"No description available."` if neither is set. |
| `documentation_link`   | No | URL to dataset documentation.                                                                                                                                      |
| `visualisation_link`   | No | URL to a visualisation of the dataset (e.g. xcube Viewer, WMS). Added as a `visualisation` link with title `"Dataset visualisation"`.                              |
| `osc_project`          | No | OSC project ID this dataset belongs to (e.g. `deep-earth-system-data-lab`). Defaults to `deep-earth-system-data-lab`.                                              |
| `cf_parameter`         | No | List of CF metadata dicts to override variable attributes (e.g. `name`, `units`).                                                                                  |
| `stac_catalog_s3_root` | Yes | S3 root where the STAC Catalog and Item are published. Publishing fails if this field is absent. See [STAC Catalog on S3](#stac-catalog-on-s3).                    |

> The fields below are only read by [`deep-code generate-prr-collection`](cli.md#generate-a-prr-collection); `publish` ignores them. "PRR-required" means the field is required by the [PRR specification](https://eoresults.esa.int/prr_collection_specifications.html), not by the command (which still runs and warns).

### PRR collection fields

| Field | Required | Description |
|---|---|---|
| `osc_initiative` | No | PRR initiative: `earthcode` or `apex` (default: `earthcode`). |
| `osc_missions` | PRR-required | List of satellite mission name(s), e.g. `[sentinel-3]`. |
| `osc_contract_number` | PRR-required | ESA contract identifier, e.g. `4000114410/15/NL/BW`. |
| `osc_project_website` | PRR-required | Project website URL. Falls back to `osc_project_url`, then `documentation_link`. |
| `osc_project_description` | PRR-required | Multi-line project description. Falls back to `description`. |
| `thumbnail` | PRR-required | URL to a collection thumbnail image (jpeg/png/webp). Added as an asset named `thumbnail` with role `thumbnail`. |
| `thumbnail_media_type` | No | Thumbnail MIME type. Guessed from the URL suffix when omitted. |
| `sci_doi` | No | Dataset DOI, e.g. `10.1000/xyz123` (a DOI name, not a link). |
| `sci_citation` | No | Human-readable citation for the dataset. |
| `prr_output_dir` | No | Local directory for the PRR collection tree. Defaults to `prr/{collection_id}`. |

`themes` for a PRR collection must be drawn from the allowed set:
`atmosphere`, `cryosphere`, `land`, `magnetosphere-ionosphere`, `oceans`, `solid-earth`
(configured via `osc_themes`). See [PRR collection output](#prr-collection-output).

### STAC Catalog on S3

`stac_catalog_s3_root` is required. deep-code writes a two-file STAC hierarchy to S3 alongside the data:

```
s3://bucket/stac/your-collection/
├── catalog.json        # STAC Catalog (root)
└── your-collection/
    └── items/
        └── your-item.json       # STAC Item covering the full Zarr store
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

### PRR collection output

[`deep-code generate-prr-collection`](cli.md#generate-a-prr-collection) writes a
self-contained STAC tree to a **local** directory (no S3 write, no GitHub PR):

```
prr/your-collection/
├── collection.json                 # STAC Collection (root, relative links)
└── your-collection/
    └── items/
        └── your-item.json         # datacube Item covering the full Zarr store
```

- **Collection** — declares the OSC, Scientific, Processing, Themes and CF extensions,
  and carries the PRR-mandatory fields (`osc:project`, `osc:initiative`,
  `osc:contract-number`, `osc:project_website`, `osc:project_description`,
  `osc:variables`, `osc:missions`, `cf:parameter`, `processing:datetime`, `themes`,
  `license`) plus a required `thumbnail` asset.
- **Item** — carries the `datacube` extension (`cube:dimensions` / `cube:variables`
  read from the Zarr) and the `zarr-data` / `zarr-consolidated-metadata` assets. Asset
  hrefs stay absolute (`s3://…`) since that is where the data lives; structural links
  are relative so the folder is portable.

The output targets the
[PRR collection specification](https://eoresults.esa.int/prr_collection_specifications.html).
Fields that can't be defaulted (`osc_missions`, `osc_contract_number`, `thumbnail`) must
be supplied in the config — otherwise the command still generates the tree but warns that
it is not yet fully conformant.

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
