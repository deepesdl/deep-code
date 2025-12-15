# Configuration

## Dataset config (YAML)
```yaml
dataset_id: your-dataset.zarr
collection_id: your-collection
osc_themes: [cryosphere]
osc_region: global
dataset_status: completed   # or ongoing/planned
documentation_link: https://example.com/docs
access_link: s3://bucket/your-dataset.zarr
```

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
