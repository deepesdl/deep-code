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
            "workflow_id": "[A unique identifier for your workflow]",
            "properties": {
                "title": "[Human-readable title of the workflow]",
                "description": "[A concise summary of what the workflow does]",
                "keywords": ["[KEYWORD1]", "[KEYWORD2]"],
                "themes": ["[Thematic area(s) of focus (e.g. land, ocean, atmosphere)]","[THEME1]", "[THEME2]"],
                "license": "[License type (e.g. MIT, Apache-2.0, CC-BY-4.0, proprietary)]",
                "jupyter_kernel_info": {
                    "name": "[Name of the execution environment or notebook kernel]",
                    "python_version": "[PYTHON_VERSION]",
                    "env_file": "[Link to the environment file (YAML) used to create the notebook environment]",
                },
            },
            "jupyter_notebook_url": "[Link to the source notebook (e.g. on GitHub)]",
            "contact": [
                {
                    "name": "[Contact person's full name]",
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
            "dataset_id": "[The name of the dataset object within your S3 bucket].zarr",
            "collection_id": "[A unique identifier for the dataset collection]",
            "osc_themes": ["[Oceans]",  "[Open Science theme (choose from "
                                           "https://opensciencedata.esa.int/themes/catalog)"],
            "osc_region": "[Geographical coverage, e.g. 'global']",
            "dataset_status": "[Status of the dataset: 'ongoing', 'completed', or 'planned']",
            "documentation_link": "[Link to relevant documentation, publication, or handbook]",
        }

        yaml_str = yaml.dump(
            template, sort_keys=False, width=1000, default_flow_style=False
        )

        if output_path:
            with open(output_path, "w") as f:
                f.write("# Complete Dataset Configuration Template\n")
                f.write("# Replace all [PLACEHOLDER] values with your actual data\n\n")
                f.write(yaml_str)
