#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.
import copy
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import fsspec
import jsonpickle
import yaml
from pystac import Catalog, Link

from deep_code.constants import (
    EXPERIMENT_BASE_CATALOG_SELF_HREF,
    OSC_BRANCH_NAME,
    OSC_REPO_NAME,
    OSC_REPO_OWNER,
    WORKFLOW_BASE_CATALOG_SELF_HREF,
)
from deep_code.utils.dataset_stac_generator import OscDatasetStacGenerator
from deep_code.utils.github_automation import GitHubAutomation
from deep_code.utils.ogc_api_record import (
    ExperimentAsOgcRecord,
    LinksBuilder,
    WorkflowAsOgcRecord,
)
from deep_code.utils.ogc_record_generator import OSCWorkflowOGCApiRecordGenerator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class GitHubPublisher:
    """
    Base class providing:
      - Reading .gitaccess for credentials
      - Common GitHub automation steps (fork, clone, branch, file commit, pull request)
    """

    def __init__(self, repo_name: str = OSC_REPO_NAME):
        with fsspec.open(".gitaccess", "r") as file:
            git_config = yaml.safe_load(file) or {}
        self.github_username = git_config.get("github-username")
        self.github_token = git_config.get("github-token")
        if not self.github_username or not self.github_token:
            raise ValueError("GitHub credentials are missing in the `.gitaccess` file.")

        self.github_automation = GitHubAutomation(
            self.github_username, self.github_token, OSC_REPO_OWNER, repo_name
        )
        self.github_automation.fork_repository()
        self.github_automation.clone_sync_repository()

    def publish_files(
        self,
        branch_name: str,
        file_dict: dict[str, dict],
        commit_message: str,
        pr_title: str,
        pr_body: str,
        base_branch: str = "main",
        sync_strategy: Literal[
            "ff", "rebase", "merge"
        ] = "merge",  # 'ff' | 'rebase' | 'merge'
    ) -> str:
        """Publish multiple files to a new branch and open a PR.

        Args:
            branch_name: Branch name to create (e.g. "osc-branch-collectionid").
            file_dict: { file_path: file_content_dict } for each file to commit.
            commit_message: Commit message for all changes.
            pr_title: Title of the pull request.
            pr_body: Description/body of the pull request.
            base_branch: Base branch to branch from and open the PR against (default: "main")
            sync_strategy: How to sync local with the remote base before pushing:
            - "ff":     Fast-forward only (no merge commits; fails if FF not possible).
            - "rebase": Rebase local changes onto the updated base branch.
            - "merge":  Create a merge commit (default).

        Returns:
            URL of the created pull request.

        Raises:
            ValueError: If an unsupported sync_strategy is provided.
        """

        if sync_strategy not in {"ff", "rebase", "merge"}:
            raise ValueError(
                f'Invalid sync_strategy="{sync_strategy}". '
                'Accepted values are "ff", "rebase", "merge".'
            )

        try:
            # Ensure local clone and remotes are ready
            self.github_automation.clone_sync_repository()
            # Sync fork with upstream before creating the branch/committing
            self.github_automation.sync_fork_with_upstream(
                base_branch=base_branch, strategy=sync_strategy
            )

            self.github_automation.create_branch(branch_name, from_branch=base_branch)

            # Add each file to the branch
            for file_path, content in file_dict.items():
                logger.info(f"Adding {file_path} to {branch_name}")
                self.github_automation.add_file(file_path, content)

            # Commit and push
            self.github_automation.commit_and_push(branch_name, commit_message)

            # Create pull request
            pr_url = self.github_automation.create_pull_request(
                branch_name, pr_title, pr_body
            )
            logger.info(f"Pull request created: {pr_url}")
            return pr_url

        finally:
            # Cleanup local clone
            self.github_automation.clean_up()


class Publisher:
    """Publishes products (datasets), workflows and experiments to the OSC GitHub
    repository.
    """

    def __init__(
        self,
        dataset_config_path: str | None = None,
        workflow_config_path: str | None = None,
        environment: str = "production",
    ):
        self.environment = environment
        # Determine repo name based on environment
        repo_name = "open-science-catalog-metadata"

        if environment == "staging":
            repo_name = "open-science-catalog-metadata-staging"
        elif environment == "testing":
            repo_name = "open-science-catalog-metadata-testing"

        # Composition
        self.gh_publisher = GitHubPublisher(repo_name=repo_name)
        self.collection_id = ""
        self.workflow_title = ""

        # Paths to configuration files, can be optional
        self.dataset_config_path = dataset_config_path
        self.workflow_config_path = workflow_config_path

        # Config dicts (loaded lazily)
        self.dataset_config: dict[str, Any] = {}
        self.workflow_config: dict[str, Any] = {}

        # Values that may be set from configs
        self.collection_id: str | None = None
        self.workflow_title: str | None = None
        self.workflow_id: str | None = None

        # Load configuration files
        self._read_config_files()

        if self.dataset_config:
            self.collection_id = self.dataset_config.get("collection_id")
        if self.workflow_config:
            self.workflow_title = self.workflow_config.get("properties", {}).get(
                "title"
            )
            self.workflow_id = self.workflow_config.get("workflow_id")

    def _read_config_files(self) -> None:
        if self.dataset_config_path:
            with fsspec.open(self.dataset_config_path, "r") as file:
                self.dataset_config = yaml.safe_load(file) or {}
        if self.workflow_config_path:
            with fsspec.open(self.workflow_config_path, "r") as file:
                self.workflow_config = yaml.safe_load(file) or {}

    @staticmethod
    def _write_to_file(file_path: str, data: dict):
        """Write a dictionary to a JSON file.

        Args:
            file_path (str): The path to the file.
            data (dict): The data to write.
        """
        # Create the directory if it doesn't exist
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            # unpicklable=False -> plain JSON (drops type metadata); cycles are resolved.
            json_content = jsonpickle.encode(data, unpicklable=False, indent=2)
        except TypeError as e:
            raise RuntimeError(f"JSON serialization failed: {e}")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_content)

    def _update_and_add_to_file_dict(
        self, file_dict, catalog_path, update_method, *args
    ):
        """Update a catalog using the specified method and add it to file_dict.

        Args:
            file_dict: The dictionary to which the updated catalog will be added.
            catalog_path: The path to the catalog file.
            update_method: The method to call for updating the catalog.
            *args: Additional arguments to pass to the update method.
        """
        full_path = (
            Path(self.gh_publisher.github_automation.local_clone_dir) / catalog_path
        )
        updated_catalog = update_method(full_path, *args)
        file_dict[full_path] = updated_catalog.to_dict()

    def _update_variable_catalogs(self, generator, file_dict, variable_ids):
        """Update or create variable catalogs and add them to file_dict.

        Args:
            generator: The generator object.
            file_dict: The dictionary to which the updated catalogs will be added.
            variable_ids: A list of variable IDs.
        """
        for var_id in variable_ids:
            var_file_path = f"variables/{var_id}/catalog.json"
            if not self.gh_publisher.github_automation.file_exists(var_file_path):
                logger.info(
                    f"Variable catalog for {var_id} does not exist. Creating..."
                )
                var_metadata = generator.variables_metadata.get(var_id)
                var_catalog = generator.build_variable_catalog(var_metadata)
                file_dict[var_file_path] = var_catalog.to_dict()
            else:
                logger.info(
                    f"Variable catalog already exists for {var_id}, adding product link."
                )
                full_path = (
                    Path(self.gh_publisher.github_automation.local_clone_dir)
                    / var_file_path
                )
                updated_catalog = generator.update_existing_variable_catalog(
                    full_path, var_id
                )
                file_dict[var_file_path] = updated_catalog.to_dict()

    def publish_dataset(
        self,
        write_to_file: bool = False,
        mode: Literal["all", "dataset", "workflow"] = "all",
    ) -> dict[str, Any]:
        """Prepare dataset/product collection for publishing to the specified GitHub
        repository."""

        if not self.dataset_config:
            raise ValueError(
                "No dataset config loaded. Provide dataset_config_path to publish dataset."
            )
        dataset_id = self.dataset_config.get("dataset_id")
        self.collection_id = self.dataset_config.get("collection_id")
        documentation_link = self.dataset_config.get("documentation_link")
        access_link = self.dataset_config.get("access_link")
        dataset_status = self.dataset_config.get("dataset_status")
        osc_region = self.dataset_config.get("osc_region")
        osc_themes = self.dataset_config.get("osc_themes")
        cf_params = self.dataset_config.get("cf_parameter")
        license_type = self.dataset_config.get("license_type")

        if not dataset_id or not self.collection_id:
            raise ValueError("Dataset ID or Collection ID missing in the config.")

        logger.info("Generating STAC collection...")

        generator = OscDatasetStacGenerator(
            dataset_id=dataset_id,
            collection_id=self.collection_id,
            workflow_id=self.workflow_id,
            workflow_title=self.workflow_title,
            license_type=license_type,
            documentation_link=documentation_link,
            access_link=access_link,
            osc_status=dataset_status,
            osc_region=osc_region,
            osc_themes=osc_themes,
            cf_params=cf_params,
        )

        variable_ids = generator.get_variable_ids()
        ds_collection = generator.build_dataset_stac_collection(mode=mode)

        # Prepare a dictionary of file paths and content
        file_dict = {}
        product_path = f"products/{self.collection_id}/collection.json"
        file_dict[product_path] = ds_collection.to_dict()

        # Update or create variable catalogs for each osc:variable
        self._update_variable_catalogs(generator, file_dict, variable_ids)

        # Update variable base catalog
        variable_base_catalog_path = "variables/catalog.json"
        self._update_and_add_to_file_dict(
            file_dict,
            variable_base_catalog_path,
            generator.update_variable_base_catalog,
            variable_ids,
        )

        # Update product base catalog
        product_catalog_path = "products/catalog.json"
        self._update_and_add_to_file_dict(
            file_dict, product_catalog_path, generator.update_product_base_catalog
        )

        # Update DeepESDL collection
        deepesdl_collection_path = "projects/deep-earth-system-data-lab/collection.json"
        self._update_and_add_to_file_dict(
            file_dict, deepesdl_collection_path, generator.update_deepesdl_collection
        )

        # Write to files if testing
        if write_to_file:
            for file_path, data in file_dict.items():
                self._write_to_file(file_path, data)  # Pass file_path and data
            return {}
        return file_dict

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        return name.replace(" ", "-").lower() if name else None

    def _update_base_catalog(
        self, catalog_path: str, item_id: str, self_href: str
    ) -> Catalog:
        """Update a base catalog by adding a unique item link and a single self link.

        Args:
            catalog_path: Path to the base catalog JSON file, relative to the repo root.
            item_id: ID (directory name) of the new item (workflow/experiment).
            self_href: Absolute self-href for the base catalog.

        Returns:
            The updated PySTAC Catalog object (in-memory).
        """
        base_catalog = Catalog.from_file(
            Path(self.gh_publisher.github_automation.local_clone_dir) / catalog_path
        )

        item_href = f"./{item_id}/record.json"

        def resolve_href(link: Link) -> str | None:
            # PySTAC keeps raw targets; get_href() may resolve relative paths if a base HREF is set
            return (
                getattr(link, "href", None)
                or getattr(link, "target", None)
                or (link.get_href() if hasattr(link, "get_href") else None)
            )

        # 1) Add the "item" link only if it's not already present
        has_item = any(
            (link.rel == "item") and (resolve_href(link) == item_href)
            for link in base_catalog.links
        )
        if not has_item:
            base_catalog.add_link(
                Link(
                    rel="item",
                    target=item_href,
                    media_type="application/json",
                    title=self.workflow_title,
                )
            )

        # 2) Ensure there is exactly one "self" link
        base_catalog.links = [link for link in base_catalog.links if link.rel != "self"]
        base_catalog.set_self_href(self_href)

        # 3) Defense-in-depth: deduplicate by (rel, href)
        seen: set[tuple[str, str | None]] = set()
        unique_links: list[Link] = []
        for link in base_catalog.links:
            key = (link.rel, resolve_href(link))
            if key not in seen:
                unique_links.append(link)
                seen.add(key)
        base_catalog.links = unique_links

        return base_catalog

    def generate_workflow_experiment_records(
        self,
        write_to_file: bool = False,
        mode: Literal["all", "dataset", "workflow"] = "all",
    ) -> dict[str, Any]:
        """prepare workflow and experiment as ogc api record to publish it to the
        specified GitHub repository."""

        file_dict = {}

        if mode not in {"workflow", "all"}:
            return file_dict  # nothing to do for mode="dataset"

        workflow_id = self._normalize_name(self.workflow_config.get("workflow_id"))
        if not workflow_id:
            raise ValueError("workflow_id is missing in workflow config.")

        properties_list = self.workflow_config.get("properties", {})
        osc_themes = properties_list.get("themes")
        contacts = self.workflow_config.get("contact", [])
        links = self.workflow_config.get("links", [])
        jupyter_notebook_url = self.workflow_config.get("jupyter_notebook_url")

        logger.info("Generating OGC API Record for the workflow...")
        rg = OSCWorkflowOGCApiRecordGenerator()
        wf_record_properties = rg.build_record_properties(properties_list, contacts)
        # make a copy for experiment record
        exp_record_properties = copy.deepcopy(wf_record_properties)
        jupyter_kernel_info = wf_record_properties.jupyter_kernel_info.to_dict()

        link_builder = LinksBuilder(osc_themes, jupyter_kernel_info)
        theme_links = link_builder.build_theme_links_for_records()
        application_link = link_builder.build_link_to_jnb(
            self.workflow_title, jupyter_notebook_url
        )
        jnb_open_link = link_builder.make_related_link_for_opening_jnb_from_github(
            jupyter_notebook_url=jupyter_notebook_url
        )

        workflow_record = WorkflowAsOgcRecord(
            id=workflow_id,
            type="Feature",
            title=self.workflow_title,
            properties=wf_record_properties,
            links=links + theme_links + application_link + jnb_open_link,
            jupyter_notebook_url=jupyter_notebook_url,
            themes=osc_themes,
        )
        if mode == "all":
            link_builder.build_child_link_to_related_experiment()
        # Convert to dictionary and cleanup
        workflow_dict = workflow_record.to_dict()
        if "jupyter_notebook_url" in workflow_dict:
            del workflow_dict["jupyter_notebook_url"]
        if "osc_workflow" in workflow_dict["properties"]:
            del workflow_dict["properties"]["osc_workflow"]
        # add workflow record to file_dict
        wf_file_path = f"workflows/{workflow_id}/record.json"
        file_dict = {wf_file_path: workflow_dict}

        # Build properties for the experiment record
        exp_record_properties.type = "experiment"
        exp_record_properties.osc_workflow = workflow_id

        # Update base catalogs of workflows with links
        file_dict["workflows/catalog.json"] = self._update_base_catalog(
            catalog_path="workflows/catalog.json",
            item_id=workflow_id,
            self_href=WORKFLOW_BASE_CATALOG_SELF_HREF,
        )

        if mode in ["all"]:
            if not getattr(self, "collection_id", None):
                raise ValueError(
                    "collection_id is required to generate the experiment record when mode='all' "
                    "(the experiment links to the output dataset)."
                )
            # generate experiment record only if there is an output dataset
            dataset_link = link_builder.build_link_to_dataset(self.collection_id)

            experiment_record = ExperimentAsOgcRecord(
                id=workflow_id,
                title=self.workflow_title,
                type="Feature",
                jupyter_notebook_url=jupyter_notebook_url,
                collection_id=self.collection_id,
                properties=exp_record_properties,
                links=links + theme_links + dataset_link,
            )
            # Convert to dictionary and cleanup
            experiment_dict = experiment_record.to_dict()
            if "jupyter_notebook_url" in experiment_dict:
                del experiment_dict["jupyter_notebook_url"]
            if "collection_id" in experiment_dict:
                del experiment_dict["collection_id"]
            if "osc:project" in experiment_dict["properties"]:
                del experiment_dict["properties"]["osc:project"]
            # add experiment record to file_dict
            exp_file_path = f"experiments/{workflow_id}/record.json"
            file_dict[exp_file_path] = experiment_dict

            # Update base catalogs of experiments with links
            file_dict["experiments/catalog.json"] = self._update_base_catalog(
                catalog_path="experiments/catalog.json",
                item_id=workflow_id,
                self_href=EXPERIMENT_BASE_CATALOG_SELF_HREF,
            )

        # Write to files if testing
        if write_to_file:
            for file_path, data in file_dict.items():
                self._write_to_file(file_path, data)
            return {}
        return file_dict

    def publish(
        self,
        write_to_file: bool = False,
        mode: Literal["all", "dataset", "workflow"] = "all",
    ) -> dict[str, Any] | str:
        """
        Publish both dataset and workflow/experiment in a single PR.
        Args:
            write_to_file: If True, write JSON files locally and return the generated dict(s).
                           If False, open a PR and return the PR URL.
            mode: Select which artifacts to publish:
                  - "dataset": only dataset collection & related catalogs
                  - "workflow": only workflow records
                  - "all": both
        Returns:
            dict[str, Any] when write_to_file=True (the files written),
            or str when write_to_file=False (the PR URL).
        """

        files: dict[str, Any] = {}

        if mode in ("dataset", "all"):
            ds_files = self.publish_dataset(write_to_file=False, mode=mode)
            files.update(ds_files)

        if mode in ("workflow", "all"):
            wf_files = self.generate_workflow_experiment_records(
                write_to_file=False, mode=mode
            )
            files.update(wf_files)

        if not files:
            raise ValueError(
                "Nothing to publish. Choose mode='dataset', 'workflow', or 'all'."
            )

        if write_to_file:
            for file_path, data in files.items():
                # file_path might be a Path (from _update_and_add_to_file_dict) – normalize to str
                out_path = str(file_path)
                self._write_to_file(out_path, data)
            return {}  # consistent with existing write_to_file behavior

        # Prepare PR
        mode_label = {
            "dataset": f"dataset: {self.collection_id or 'unknown'}",
            "workflow": f"workflow: {self.workflow_id or 'unknown'}",
            "all": f"dataset: {self.collection_id or 'unknown'} + workflow/experiment: {self.workflow_id or 'unknown'}",
        }[mode]

        branch_name = (
            f"{OSC_BRANCH_NAME}-{(self.collection_id or self.workflow_id or 'osc')}"
            f"-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        commit_message = f"Publish {mode_label}"
        pr_title = f"Publish {mode_label}"
        pr_body = f"This PR publishes {mode_label} to the repository."

        pr_url = self.gh_publisher.publish_files(
            branch_name=branch_name,
            file_dict=files,
            commit_message=commit_message,
            pr_title=pr_title,
            pr_body=pr_body,
        )
        logger.info(f"Pull request created: {pr_url}")
        return pr_url
