#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

from typing import Optional

import yaml


class TemplateGenerator:
    @staticmethod
    def generate_workflow_template(output_path: Optional[str] = None) -> str:
        """Generate a complete template with all possible keys and placeholder values"""

        workflow_template = {
            "workflow_id": "[REQUIRED: unique identifier for your workflow]",
            "properties": {
                "title": "[REQUIRED: human-readable title of the workflow]",
                "license": "[REQUIRED: SPDX license identifier, e.g. CC-BY-4.0, MIT, proprietary]",
                "description": "[OPTIONAL: concise summary of what the workflow does]",
                "keywords": ["[OPTIONAL: KEYWORD1]", "[KEYWORD2]"],
                "themes": ["[OPTIONAL: thematic area, e.g. land, ocean, atmosphere]"],
                "jupyter_kernel_info": {
                    "name": "[OPTIONAL: name of the execution environment or notebook kernel]",
                    "python_version": "[PYTHON_VERSION]",
                    "env_file": "[Link to the environment file (YAML) used to create the notebook environment]",
                },
            },
            "jupyter_notebook_url": "[OPTIONAL: link to the source notebook (e.g. on GitHub)]",
            "parameters": {
                "[OPTIONAL: PARAM_NAME]": "[PARAM_VALUE]",
            },
            "input_datasets": [
                "[OPTIONAL: dataset ID or URL used as input to the workflow]",
            ],
            "contact": [
                {
                    "name": "[OPTIONAL: contact person's full name]",
                    "organization": "[Affiliated institution or company]",
                    "links": [
                        {
                            "rel": "about",
                            "type": "text/html",
                            "href": "[ORGANIZATION_URL]",
                        }
                    ],
                }
            ],
        }

        if output_path:
            with open(output_path, "w") as f:
                f.write("# Workflow Configuration Template\n")
                f.write("# Replace all [PLACEHOLDER] values with your actual data\n\n")
                f.write(yaml.dump(workflow_template, sort_keys=False, width=1000,
                                  default_flow_style=False))

    @staticmethod
    def generate_dataset_template(output_path: Optional[str] = None) -> str:
        """Generate a complete dataset template with all possible keys and placeholder values"""

        required = {
            "dataset_id": "[REQUIRED: name of the Zarr store in your S3 bucket, e.g. my-dataset.zarr]",
            "collection_id": "[REQUIRED: unique identifier, no spaces — use hyphens (e.g. My-Dataset-2024)]",
            "license_type": "[REQUIRED: SPDX license identifier, e.g. CC-BY-4.0, MIT, proprietary]",
            "stac_catalog_s3_root": "[REQUIRED: S3 root for the STAC Catalog + Item, e.g. s3://my-bucket/stac/my-collection/]",
        }

        optional = {
            "osc_themes": ["[OPTIONAL: OSC theme slug, e.g. land, ocean, atmosphere — auto-lowercased]"],
            "osc_region": "[OPTIONAL: geographical coverage, e.g. Global]",
            "dataset_status": "[OPTIONAL: ongoing | completed | planned (default: ongoing)]",
            "description": "[OPTIONAL: human-readable description of the dataset. Overrides the description attribute in the Zarr store if set]",
            "documentation_link": "[OPTIONAL: link to documentation, publication, or handbook]",
            "visualisation_link": "[OPTIONAL: URL to a visualisation of the dataset (e.g. xcube Viewer, WMS)]",
            "osc_project": "[OPTIONAL: OSC project ID (e.g. deep-earth-system-data-lab). Defaults to deep-earth-system-data-lab]",
            "osc_project_title": "[OPTIONAL: display title of the OSC project as it appears in the catalog (e.g. DeepESDL). Defaults to a formatted version of osc_project if omitted]",
            "access_link": "[OPTIONAL: public S3 URL of the Zarr store — defaults to s3://deep-esdl-public/{dataset_id}]",
            "cf_parameter": [{"name": "[OPTIONAL: CF standard name]", "units": "[unit string]"}],
        }

        stac_catalog_comment = (
            "\n# stac_catalog_s3_root: deep-code writes the following files to this S3 root:\n"
            "#   {stac_catalog_s3_root}/catalog.json               (STAC Catalog root)\n"
            "#   {stac_catalog_s3_root}/{collection_id}/item.json  (STAC Item for the whole Zarr)\n"
            "# S3 write credentials are resolved in order:\n"
            "#   1. STAC_S3_KEY / STAC_S3_SECRET env vars (STAC-specific, any bucket)\n"
            "#   2. AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars\n"
            "#   3. boto3 default chain (IAM role, ~/.aws/credentials)\n"
        )

        if output_path:
            with open(output_path, "w") as f:
                f.write("# Dataset Configuration Template\n")
                f.write("# Replace all [PLACEHOLDER] values with your actual data\n\n")
                f.write("# --- REQUIRED fields ---\n")
                f.write(yaml.dump(required, sort_keys=False, width=1000, default_flow_style=False))
                f.write("\n# --- OPTIONAL fields ---\n")
                f.write(yaml.dump(optional, sort_keys=False, width=1000, default_flow_style=False))
                f.write(stac_catalog_comment)
