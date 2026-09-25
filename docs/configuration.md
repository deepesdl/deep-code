# Configuration

The quickest way to get started is to generate starter templates with the CLI:

```bash
deep-code generate-config              # writes to current directory
deep-code generate-config -o ./configs # custom output folder
```

This creates `dataset.yaml` and `workflow.yaml` with all supported fields and placeholder values. Fill them in, then run [`deep-code publish`](cli.md#publish-metadata).

The sections below document every field in those templates.

---

## Dataset config (YAML)
```yaml
# Required
collection_id: your-collection       # no spaces — use hyphens
license_type: CC-BY-4.0
items_config:
  - dataset_id: your-dataset.zarr
    item_id: your-item               # no spaces — use hyphens
osc_project: osc-project-name
osc_project_url: osc-project-url

# Optional
osc_themes: [cryosphere]        # must match slugs at opensciencedata.esa.int/themes/catalog — auto-lowercased
osc_region: global
osc_status: completed           # ongoing | completed | planned (default: completed)
documentation_link: https://example.com/docs
visualisation_link: https://example.com/viewer   # URL to a visualisation of the dataset
stac_catalog_s3_root: s3://bucket/stac/your-collection/   # only for datasets not in PRR
access_link: https://example.com/your-dataset.zarr   # only with stac_catalog_s3_root; defaults to the PRR item's Zarr asset

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
coord_position: center           # center | left | right (default: center)
prr_output_dir: ./prr/your-collection
```

### Field reference

| Field                  | Required | Description                                                                                                                                                  |
|------------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `collection_id`        | Yes      | Unique ID for the STAC collection in the OSC catalog. **Must not contain spaces** — use hyphens as word separators (e.g. `My-Collection-2024`).              |
| `license_type`         | Yes      | SPDX license identifier (e.g. `CC-BY-4.0`). Publishing fails if this field is absent.                                                                        |
| `items_config`         | Yes      | List of `{dataset_id, item_id}` entries. Use one entry for `publish` today; the generator can emit multiple items when more are provided.                    |
| `osc_project`          | Yes      | OSC project ID this dataset belongs to (e.g. `deep-earth-system-data-lab`).                                                                                  |
| `osc_project_url`      | Yes      | OSC project url used to link to project.                                                                                                                     |
| `osc_themes`           | No       | List of OSC theme slugs (e.g. `[cryosphere, oceans]`). Values are automatically lowercased so `Land` and `land` are equivalent.                              |
| `osc_region`           | No       | Geographical region label (default: `Global`).                                                                                                               |
| `osc_status`           | No       | One of `ongoing`, `completed`, or `planned` (default: `completed`).                                                                                          |
| `stac_catalog_s3_root` | No       | S3 root to publish a deep-code STAC Catalog and Item to, for datasets **not** in PRR. When omitted (the default), the OSC collection links to the dataset's PRR collection instead. See [Data links](#data-links). |
| `access_link`          | No       | Only used with `stac_catalog_s3_root`. Absolute URL of the Zarr store, used as the asset href of the S3 STAC item. Defaults to the `zarr-data` asset of the dataset's item in the PRR STAC API. |
| `description`          | No       | Human-readable description of the dataset. Overrides the `description` attribute in the Zarr store; falls back to `"No description available."` if neither is set. |
| `documentation_link`   | No       | URL to dataset documentation.                                                                                                                                |
| `visualisation_link`   | No       | URL to a visualisation of the dataset (e.g. xcube Viewer, WMS). Added as a `visualisation` link with title `"Dataset visualisation"`.                        |
| `cf_parameter`         | No       | List of CF metadata dicts to override variable attributes (e.g. `name`, `units`).                                                                            |

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
| `coord_position` | No | Where each coordinate value sits within its grid cell: `center` (cell centres), `left` (left/bottom edge) or `right` (right/top edge). Default `center`. Controls how the bounding box and `cube:dimensions` extents are expanded from the coordinate values to the outer edges of the data — see [Coordinate position](#coordinate-position). |
| `prr_output_dir` | No | Local directory for the PRR collection tree. Defaults to `prr/{collection_id}`. |

`themes` for a PRR collection must be drawn from the allowed set:
`atmosphere`, `cryosphere`, `land`, `magnetosphere-ionosphere`, `oceans`, `solid-earth`
(configured via `osc_themes`). See [PRR collection output](#prr-collection-output).

### Coordinate position

A dataset's spatial coordinates are single values per grid cell, but a STAC
bounding box describes the *outer edges* of the area covered. `coord_position`
tells deep-code which part of the cell the stored coordinates refer to, so the
extent can be expanded by the right amount:

| Value | Coordinates represent | Extent derived as |
|---|---|---|
| `center` (default) | cell centres | `min - res/2` … `max + res/2` |
| `left` | the left/bottom edge of each cell | `min` … `max + res` |
| `right` | the right/top edge of each cell | `min - res` … `max` |

`res` is the grid resolution, taken from the spacing between adjacent
coordinates. For example, a 1° global grid stored with cell centres at
`-179.5 … 179.5` covers `-180 … 180`; with `coord_position: center` the
reported bbox is the full `-180 … 180` rather than the 1°-too-small
`-179.5 … 179.5`.

The setting applies to both the collection/item `bbox` and the
`cube:dimensions` extents of the datacube extension, and to the `x`/`y` axes
alike. An invalid value raises a `ValueError`.

### Data links

The OSC collection links to where the data can be accessed, following the OSC
convention of a `via` link (human-browsable) and a `child` link (machine-readable).

#### Default: PRR collection

By default the dataset is expected to be in the ESA Project Results Repository
(PRR), and the OSC collection links to its PRR collection:

- `via` (title `Access`) — `https://eoresults.esa.int/browser/#/external/eoresults.esa.int/stac/collections/{collection_id}`
- `child` — `https://eoresults.esa.int/stac/collections/{collection_id}`

Nothing is written to S3 and no S3 credentials are needed. **Ingest the dataset
into PRR before publishing to OSC** (see
[Generate a PRR collection](cli.md#generate-a-prr-collection)); publishing fails
with an error if the PRR collection does not exist.

#### STAC Catalog on S3

For datasets that are not in PRR, set `stac_catalog_s3_root`. deep-code then
writes a two-file STAC hierarchy to S3 and links it instead of PRR:

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

Both asset hrefs are absolute. Set `access_link` to the Zarr store's URL; if it
is omitted, deep-code looks the href up from the `zarr-data` asset of the
dataset's PRR item
(`https://eoresults.esa.int/stac/collections/{collection_id}/items/{item_id}`)
and fails with an error if that item cannot be found.

The OSC collection links to the S3 catalog:

- `via` — the catalog in the OSC STAC browser (human-browsable).
- `child` — the direct HTTPS URL of `catalog.json` (machine-readable).

The `s3://` URL is converted to HTTPS because raw `s3://` URLs fail the
`uri-reference` format check of the OSC products schema.

S3 credentials for writing the STAC catalog are resolved in this order:
`STAC_S3_KEY` / `STAC_S3_SECRET` env vars (STAC-specific, can target any bucket),
then `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`,
then the boto3 default chain (IAM role, `~/.aws/credentials`).

### PRR collection output

[`deep-code generate-prr-collection`](cli.md#generate-a-prr-collection) writes a
self-contained STAC tree to a **local** directory (no S3 write, no GitHub PR):

```
prr/
└── {collection_id}/
    └── collection.json            # STAC Collection (root)
    └── items
        └── {item_id_0}.json       # datacube Item (whole Zarr)
        └── {item_id_1}.json       # datacube Item (whole Zarr)
```

- **Collection** — declares the OSC, Scientific, Processing, Themes and CF extensions,
  and carries the PRR-mandatory fields (`osc:project`, `osc:initiative`,
  `osc:contract-number`, `osc:project_website`, `osc:project_description`,
  `osc:variables`, `osc:missions`, `cf:parameter`, `processing:datetime`, `themes`,
  `license`) plus a required `thumbnail` asset.
- **Item** — carries the `datacube` extension (`cube:dimensions` / `cube:variables`
  read from the Zarr) and the `zarr-data` / `zarr-consolidated-metadata` assets. Asset
  hrefs are relative (`./{dataset_id}`) because PRR ingests the Zarr store next to
  the item; structural links are relative too, so the folder is portable.

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

More templates and examples live in `dataset.yaml`, `workflow.yaml`, and `example-config/`.
