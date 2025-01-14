#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import fsspec
import logging
import yaml
from pathlib import Path

from deep_code.constants import OSC_REPO_OWNER, OSC_REPO_NAME, OSC_BRANCH_NAME
from deep_code.utils.dataset_stac_generator import OSCDatasetSTACGenerator
from deep_code.utils.github_automation import GitHubAutomation

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DatasetPublisher:
    """
    Publishes products to the OSC GitHub repository.

    Credentials must be provided via a hidden file named `.gitaccess`, located in
    the root of the repository. This file is expected to contain YAML of the form:

        github-username: "YOUR_GITHUB_USERNAME"
        github-token: "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
    """

    def __init__(self):
        with fsspec.open(".gitaccess", "r") as file:
            git_config = yaml.safe_load(file) or {}

        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")

        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the `.gitaccess` file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, OSC_REPO_NAME
        )

    def publish_dataset(self, dataset_config_path: str):
        """Publish a product collection to the specified GitHub repository.

        Args:
             dataset_config_path: Path to the YAML file containing dataset config
        """
        with fsspec.open(dataset_config_path, "r") as file:
            dataset_config = yaml.safe_load(file)

        dataset_id = dataset_config.get("dataset_id")
        collection_id = dataset_config.get("collection_id")
        documentation_link = dataset_config.get("documentation_link")
        access_link = dataset_config.get("access_link")
        dataset_status = dataset_config.get("dataset_status")
        osc_region = dataset_config.get("osc_region")
        osc_themes = dataset_config.get("osc_themes")
        cf_params = dataset_config.get("cf_parameter")

        if not dataset_id or not collection_id:
            raise ValueError(
                "Dataset ID or Collection ID is missing in the dataset-config.yaml "
                "file."
            )

        try:
            logger.info("Generating STAC collection...")
            generator = OSCDatasetSTACGenerator(
                dataset_id=dataset_id,
                collection_id=collection_id,
                documentation_link=documentation_link,
                access_link=access_link,
                osc_status=dataset_status,
                osc_region=osc_region,
                osc_themes=osc_themes,
                cf_params=cf_params,
            )
            var_catalogs = generator.get_variables_and_build_catalog()
            ds_collection = generator.build_dataset_stac_collection()

            file_path = f"products/{collection_id}/collection.json"
            logger.info("Automating GitHub tasks...")

            self.github_automation.fork_repository()
            self.github_automation.clone_repository()
            OSC_NEW_BRANCH_NAME = OSC_BRANCH_NAME + "-" + collection_id
            self.github_automation.create_branch(OSC_NEW_BRANCH_NAME)

            for var_id, var_catalog in var_catalogs.items():
                var_file_path = f"variables/{var_id}/catalog.json"
                if not self.github_automation.file_exists(var_file_path):
                    logger.info(
                        f"Variable catalog for {var_id} does not exist. Creating..."
                    )
                    self.github_automation.add_file(
                        var_file_path, var_catalog.to_dict()
                    )
                else:
                    logger.info(
                        f"Variable catalog already exists for {var_id}. so add the "
                        f"product as child link..."
                    )
                    full_path = (
                        Path(self.github_automation.local_clone_dir) / var_file_path
                    )
                    self.github_automation.add_file(
                        var_file_path,
                        generator.update_existing_variable_catalog(
                            full_path, var_id
                        ).to_dict(),
                    )

            self.github_automation.add_file(file_path, ds_collection.to_dict())

            self.github_automation.commit_and_push(
                OSC_NEW_BRANCH_NAME, f"Add new collection:{collection_id}"
            )
            pr_url = self.github_automation.create_pull_request(
                OSC_NEW_BRANCH_NAME,
                f"Add new dataset collection",
                "This PR adds a new collection to the repository.",
            )

            logger.info(f"Pull request created: {pr_url}")

        finally:
            self.github_automation.clean_up()
