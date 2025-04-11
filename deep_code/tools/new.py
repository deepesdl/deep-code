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

        template = {
            "workflow_id": "[WORKFLOW_ID]",
            "properties": {
                "title": "[TITLE]",
                "description": "[DESCRIPTION]",
                "keywords": ["[KEYWORD1]", "[KEYWORD2]"],
                "themes": ["[THEME1]", "[THEME2]"],
                "license": "[LICENSE_TYPE]",
                "jupyter_kernel_info": {
                    "name": "[DEEPESDL_KERNEL_NAME]",
                    "python_version": "[PYTHON_VERSION]",
                    "env_file": "[ENV_FILE_URL_IN_GIT]",
                },
            },
            "jupyter_notebook_url": "[NOTEBOOK_URL]",
            "contact": [
                {
                    "name": "[CONTACT_NAME]",
                    "organization": "[ORGANIZATION]",
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

        yaml_str = yaml.dump(
            template, sort_keys=False, width=1000, default_flow_style=False
        )

        if output_path:
            with open(output_path, "w") as f:
                f.write("# Complete Workflow Configuration Template\n")
                f.write("# Replace all [PLACEHOLDER] values with your actual data\n\n")
                f.write(yaml_str)

    @staticmethod
    def generate_dataset_template(output_path: Optional[str] = None) -> str:
        """Generate a complete dataset template with all possible keys and placeholder values"""

        template = {
            "dataset_id": "[DATASET_ID].zarr",
            "collection_id": "[COLLECTION_ID]",
            "osc_themes": ["[THEME1]", "[THEME2]"],
            "osc_region": "[REGION]",
            "dataset_status": "[STATUS]",
            "documentation_link": "[DOCS_URL]",
        }

        yaml_str = yaml.dump(
            template, sort_keys=False, width=1000, default_flow_style=False
        )

        if output_path:
            with open(output_path, "w") as f:
                f.write("# Complete Dataset Configuration Template\n")
                f.write("# Replace all [PLACEHOLDER] values with your actual data\n\n")
                f.write(yaml_str)
