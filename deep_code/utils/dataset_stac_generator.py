#!/usr/bin/env python3
# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import pyproj
import xarray as xr
from pystac import (
    Asset,
    Catalog,
    CatalogType,
    Collection,
    Extent,
    Item,
    Link,
    SpatialExtent,
    TemporalExtent,
)

from deep_code.constants import (
    CONTACTS_SCHEMA_URI,
    DATACUBE_SCHEMA_URI,
    OSC_SCHEMA_URI,
    OSC_THEME_SCHEME,
    PROCESSING_SCHEMA_URI,
    SCIENTIFIC_SCHEMA_URI,
    THEMES_SCHEMA_URI,
    ZARR_MEDIA_TYPE,
)
from deep_code.utils.helper import open_dataset
from deep_code.utils.ogc_api_record import Theme, ThemeConcept
from deep_code.utils.osc_extension import OscExtension


@dataclass
class ItemConfig:
    dataset_id: str
    item_id: str


class OscDatasetStacGenerator:
    """Generates OSC STAC Collections for a product from Zarr datasets.

    Args:
        collection_id: Unique identifier for the STAC collection.
        items_config: List of item configuration entries. Each item maps one
            dataset_id to one item_id
        access_link_root: Public access link to the root of the datasets.
        documentation_link: Link to dataset documentation.
        osc_status: Status of the dataset (e.g., "ongoing").
        osc_region: Geographical region associated with the dataset.
        osc_themes: List of themes related to the dataset (e.g., ["climate"]).
        osc_missions: List of satellite missions associated with the dataset.
        cf_params: CF metadata parameters for the dataset.
        osc_project: OSC project identifier (default: "deep-earth-system-data-lab").
    """

    def __init__(
        self,
        collection_id: str,
        items_config: list[ItemConfig],
        workflow_id: str,
        workflow_title: str,
        license_type: str,
        osc_project: str,
        access_link_root: str | None = None,
        documentation_link: str | None = None,
        osc_status: str = "ongoing",
        osc_region: str = "Global",
        osc_themes: list[str] | None = None,
        osc_missions: list[str] | None = None,
        cf_params: list[dict[str, Any]] | None = None,
        osc_project_title: str | None = None,
        osc_project_url: str | None = None,
        visualisation_link: str | None = None,
        description: str | None = None,
        osc_initiative: str = "earthcode",
        osc_contract_number: str | None = None,
        osc_project_website: str | None = None,
        osc_project_description: str | None = None,
        thumbnail: str | None = None,
        thumbnail_media_type: str | None = None,
        sci_doi: str | None = None,
        sci_citation: str | None = None,
    ):
        if " " in collection_id:
            raise ValueError(
                f"collection_id must not contain spaces: {collection_id!r}. "
                "Use hyphens as word separators (e.g. 'My-Collection-2024')."
            )
        self.collection_id = collection_id
        self.items_config = items_config
        self.workflow_id = workflow_id
        self.workflow_title = workflow_title
        self.license_type = license_type
        self.osc_project = osc_project
        self.osc_project_title = osc_project_title or osc_project
        self.osc_project_url = osc_project_url
        self.access_link_root = access_link_root or "s3://deep-esdl-public/"
        self.documentation_link = documentation_link
        self.osc_status = osc_status
        self.osc_region = osc_region
        self.osc_themes = [t.lower() for t in (osc_themes or [])]
        self.osc_missions = osc_missions or []
        self.cf_params = cf_params or {}
        self.visualisation_link = visualisation_link
        self.description = description
        # PRR-specific project metadata (see PRR collection specification).
        self.osc_initiative = osc_initiative or "earthcode"
        self.osc_contract_number = osc_contract_number
        self.osc_project_website = osc_project_website
        self.osc_project_description = osc_project_description
        self.thumbnail = thumbnail
        self.thumbnail_media_type = thumbnail_media_type
        self.sci_doi = sci_doi
        self.sci_citation = sci_citation
        self.logger = logging.getLogger(__name__)

    def _get_spatial_extent(self, dataset: xr.Dataset) -> SpatialExtent:
        """Extract the spatial extent and return it in EPSG:4326."""

        if {"lon", "lat"}.issubset(dataset.coords):
            x_name, y_name = "lon", "lat"
        elif {"longitude", "latitude"}.issubset(dataset.coords):
            x_name, y_name = "longitude", "latitude"
        elif {"x", "y"}.issubset(dataset.coords):
            x_name, y_name = "x", "y"
        else:
            raise ValueError(
                "Dataset does not have recognized spatial coordinates "
                "('lon', 'lat'), ('longitude', 'latitude'), or ('x', 'y')."
            )

        x_min = float(dataset[x_name].min())
        x_max = float(dataset[x_name].max())
        y_min = float(dataset[y_name].min())
        y_max = float(dataset[y_name].max())

        crs = self._get_crs(dataset)

        if crs.to_epsg() != 4326:
            transformer = pyproj.Transformer.from_crs(crs, 4326, always_xy=True)
            x_min, y_min, x_max, y_max = transformer.transform_bounds(
                x_min, y_min, x_max, y_max
            )

        return SpatialExtent([[x_min, y_min, x_max, y_max]])

    @staticmethod
    def _get_temporal_extent(dataset: xr.Dataset) -> TemporalExtent:
        """Extract temporal extent from the dataset."""
        dataset = dataset
        if "time" in dataset.coords:
            try:
                # Convert the time bounds to datetime objects
                time_min = pd.to_datetime(dataset.time.min().values).to_pydatetime()
                time_max = pd.to_datetime(dataset.time.max().values).to_pydatetime()
                return TemporalExtent([[time_min, time_max]])
            except Exception as e:
                raise ValueError(f"Failed to parse temporal extent: {e}")
        else:
            raise ValueError("Dataset does not have a 'time' coordinate.")

    @staticmethod
    def _normalize_name(name: str | None) -> str | None:
        if name:
            return name.replace(" ", "-").replace("_", "-").lower()
        return None

    def _build_access_link(self, item_config: ItemConfig) -> str:
        """Return the asset href for an item, supporting prefix and full URLs."""
        root = self.access_link_root
        if root.endswith("/"):
            root = root.rstrip("/")
        return f"{root}/{item_config.dataset_id}"

    @staticmethod
    def _union_spatial_extent(items: list[Item]) -> SpatialExtent:
        """Merge multiple dataset spatial extents into a single bounding box."""
        bboxes = [item.bbox for item in items]
        return SpatialExtent(
            [
                [
                    min(bbox[0] for bbox in bboxes),
                    min(bbox[1] for bbox in bboxes),
                    max(bbox[2] for bbox in bboxes),
                    max(bbox[3] for bbox in bboxes),
                ]
            ]
        )

    @staticmethod
    def _union_temporal_extent(items: list[Item]) -> TemporalExtent:
        """Merge multiple dataset temporal extents into a single interval."""
        intervals = np.array(
            [
                [
                    datetime.fromisoformat(item.properties["start_datetime"]),
                    datetime.fromisoformat(item.properties["end_datetime"]),
                ]
                for item in items
            ]
        )
        return TemporalExtent([[min(intervals[:, 0]), max(intervals[:, 1])]])

    def _get_general_metadata(self, dataset: xr.Dataset) -> dict:
        return {
            "description": (
                self.description
                or dataset.attrs.get("description")
                or "No description available."
            )
        }

    def extract_metadata_for_variable(self, variable_data) -> dict:
        """Extract metadata for a single variable."""
        long_name = variable_data.attrs.get("long_name")
        standard_name = variable_data.attrs.get("standard_name")
        variable_id = standard_name or variable_data.name
        description = variable_data.attrs.get("description", long_name)
        gcmd_keyword_url = variable_data.attrs.get("gcmd_keyword_url")
        return {
            "variable_id": self._normalize_name(variable_id),
            "description": description,
            "gcmd_keyword_url": gcmd_keyword_url,
        }

    def get_variable_ids(self, dataset: xr.Dataset) -> list[str]:
        """Get variable IDs for all variables in the dataset."""
        variable_ids = list(self.get_variables_metadata(dataset).keys())
        #  Remove 'crs' and 'spatial_ref' from the list if they exist, note that
        #  spatial_ref will be normalized to spatial-ref in variable_ids and skipped.
        return [
            var_id for var_id in variable_ids if var_id not in ["crs", "spatial-ref"]
        ]

    def get_variables_metadata(self, dataset: xr.Dataset) -> dict[str, dict]:
        """Extract metadata for all variables in the dataset."""
        variables_metadata = {}
        for variable in dataset.data_vars.values():
            var_metadata = self.extract_metadata_for_variable(variable)
            variables_metadata[var_metadata.get("variable_id")] = var_metadata
        return variables_metadata

    def _add_gcmd_link_to_var_catalog(
        self, var_catalog: Catalog, var_metadata: dict
    ) -> None:
        """
        Checks for a GCMD keyword URL in var_metadata, adds a 'via' link to the catalog
        pointing to the GCMD Keyword Viewer.

        Args:
            var_catalog: The PySTAC Catalog to which we want to add the link.
            var_metadata: Dictionary containing metadata about the variable,
                          including 'gcmd_keyword_url'.
        """
        gcmd_keyword_url = var_metadata.get("gcmd_keyword_url")
        if not gcmd_keyword_url:
            gcmd_keyword_url = input(
                f"Enter GCMD keyword URL or a similar url for"
                f" {var_metadata.get('variable_id')}: "
            ).strip()
        var_catalog.add_link(
            Link(
                rel="via",
                target=gcmd_keyword_url,
                title="Description",
                media_type="text/html",
            )
        )
        self.logger.info(
            f'Added GCMD link for {var_metadata.get("variable_id")} '
            f"catalog {gcmd_keyword_url}."
        )

    def build_variable_catalog(self, var_metadata) -> Catalog:
        """Build an OSC STAC Catalog for the variables in the dataset.

        Returns:
            A pystac.Catalog object.
        """
        var_id = var_metadata.get("variable_id")
        concepts = [{"id": theme} for theme in self.osc_themes]

        themes = [
            {
                "scheme": "https://github.com/stac-extensions/osc#theme",
                "concepts": concepts,
            }
        ]

        now_iso = datetime.now(timezone.utc).isoformat()

        # Create a PySTAC Catalog object
        var_catalog = Catalog(
            id=var_id,
            description=var_metadata.get("description") or self.format_string(var_id),
            title=self.format_string(var_id),
            stac_extensions=[
                "https://stac-extensions.github.io/themes/v1.0.0/schema.json"
            ],
        )

        var_catalog.stac_version = "1.0.0"
        var_catalog.extra_fields["updated"] = now_iso
        var_catalog.keywords = []

        # Add the 'themes' block (from your example JSON)
        var_catalog.extra_fields["themes"] = themes

        var_catalog.remove_links("root")
        # Add relevant links
        var_catalog.add_link(
            Link(
                rel="root",
                target="../../catalog.json",
                media_type="application/json",
                title="Open Science Catalog",
            )
        )

        # 'child' link: points to the product (or one of its collections) using this variable
        var_catalog.add_link(
            Link(
                rel="child",
                target=f"../../products/{self.collection_id}/collection.json",
                media_type="application/json",
                title=self.collection_id,
            )
        )

        # 'parent' link: back up to the variables overview
        var_catalog.add_link(
            Link(
                rel="parent",
                target="../catalog.json",
                media_type="application/json",
                title="Variables",
            )
        )
        # Add gcmd link for the variable definition
        self._add_gcmd_link_to_var_catalog(var_catalog, var_metadata)

        self.add_themes_as_related_links_var_catalog(var_catalog)

        self_href = (
            f"https://esa-earthcode.github.io/open-science-catalog-metadata/variables"
            f"/{var_id}/catalog.json"
        )
        # 'self' link: the direct URL where this JSON is hosted
        var_catalog.set_self_href(self_href)

        return var_catalog

    @staticmethod
    def _append_link_if_absent(links: list, new_link: dict) -> None:
        """Append *new_link* to *links* only when no existing entry has the
        same ``rel`` and ``href`` (prevents duplicates on repeated publishes)."""
        if not any(
            lnk.get("rel") == new_link["rel"] and lnk.get("href") == new_link["href"]
            for lnk in links
        ):
            links.append(new_link)

    def update_product_base_catalog(self, product_catalog_path) -> dict:
        """Append a child link to the products base catalog and return the
        modified JSON dict without touching any existing links."""
        with open(product_catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        self._append_link_if_absent(
            data.setdefault("links", []),
            {
                "rel": "child",
                "href": f"./{self.collection_id}/collection.json",
                "type": "application/json",
                "title": self.collection_id,
            },
        )
        return data

    def update_variable_base_catalog(
        self, variable_base_catalog_path, variable_ids
    ) -> dict:
        """Append child links for each variable to the variables base catalog."""
        with open(variable_base_catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        links = data.setdefault("links", [])
        for var_id in variable_ids:
            self._append_link_if_absent(
                links,
                {
                    "rel": "child",
                    "href": f"./{var_id}/catalog.json",
                    "type": "application/json",
                    "title": self.format_string(var_id),
                },
            )
        return data

    def add_themes_as_related_links_var_catalog(self, var_catalog):
        """Add themes as related links to variable catalog"""
        for theme in self.osc_themes:
            var_catalog.add_link(
                Link(
                    rel="related",
                    target=f"../../themes/{theme}/catalog.json",
                    media_type="application/json",
                    title=f"Theme: {self.format_string(theme)}",
                )
            )

    def build_project_collection(self) -> dict:
        """Build a minimal STAC Collection JSON dict for the OSC project.

        Used when the project collection does not yet exist in the catalog.

        Returns:
            A plain dict representing the STAC Collection.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        self_href = (
            "https://esa-earthcode.github.io/open-science-catalog-metadata"
            f"/projects/{self.osc_project}/collection.json"
        )
        links = [
            {
                "rel": "self",
                "href": self_href,
                "type": "application/json",
            },
            {
                "rel": "root",
                "href": "../../catalog.json",
                "type": "application/json",
                "title": "Open Science Catalog",
            },
            {
                "rel": "parent",
                "href": "../catalog.json",
                "type": "application/json",
                "title": "Projects",
            },
        ]
        project_url = self.osc_project_url or self.documentation_link
        if project_url:
            links.append(
                {
                    "rel": "via",
                    "href": project_url,
                    "type": "text/html",
                    "title": self.osc_project_title,
                }
            )
        else:
            self.logger.warning(
                "No 'osc_project_url' or 'documentation_link' provided. "
                "The project collection will be missing a required 'via' link."
            )
        themes = (
            [
                {
                    "concepts": [{"id": theme} for theme in self.osc_themes],
                    "scheme": OSC_THEME_SCHEME,
                }
            ]
            if self.osc_themes
            else []
        )
        return {
            "type": "Collection",
            "id": self.osc_project,
            "stac_version": "1.0.0",
            "stac_extensions": [
                OSC_SCHEMA_URI,
                THEMES_SCHEMA_URI,
                CONTACTS_SCHEMA_URI,
            ],
            "title": self.format_string(self.osc_project_title or self.osc_project),
            "description": self.format_string(
                self.osc_project_title or self.osc_project
            ),
            "keywords": [],
            "license": "various",
            "extent": {
                "spatial": {"bbox": [[-180, -90, 180, 90]]},
                "temporal": {"interval": [[None, None]]},
            },
            "created": now_iso,
            "updated": now_iso,
            "osc:type": "project",
            "osc:status": self.osc_status,
            "themes": themes,
            "contacts": [],
            "links": links,
        }

    def update_project_base_catalog(self, project_base_catalog_path) -> dict:
        """Append a child link for the project to the projects base catalog."""
        with open(project_base_catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        self._append_link_if_absent(
            data.setdefault("links", []),
            {
                "rel": "child",
                "href": f"./{self.osc_project}/collection.json",
                "type": "application/json",
                "title": self.format_string(self.osc_project),
            },
        )
        return data

    def update_deepesdl_collection(self, deepesdl_collection_full_path) -> dict:
        """Append child and theme-related links to the DeepESDL collection."""
        with open(deepesdl_collection_full_path, encoding="utf-8") as f:
            data = json.load(f)
        links = data.setdefault("links", [])
        self._append_link_if_absent(
            links,
            {
                "rel": "child",
                "href": f"../../products/{self.collection_id}/collection.json",
                "type": "application/json",
                "title": self.collection_id,
            },
        )
        for theme in self.osc_themes:
            self._append_link_if_absent(
                links,
                {
                    "rel": "related",
                    "href": f"../../themes/{theme}/catalog.json",
                    "type": "application/json",
                    "title": f"Theme: {self.format_string(theme)}",
                },
            )
        return data

    def update_existing_variable_catalog(self, var_file_path) -> dict:
        """Append child and theme links to an existing variable catalog."""
        with open(var_file_path, encoding="utf-8") as f:
            data = json.load(f)
        data["updated"] = datetime.now(timezone.utc).isoformat()
        links = data.setdefault("links", [])
        self._append_link_if_absent(
            links,
            {
                "rel": "child",
                "href": f"../../products/{self.collection_id}/collection.json",
                "type": "application/json",
                "title": self.collection_id,
            },
        )
        for theme in self.osc_themes:
            self._append_link_if_absent(
                links,
                {
                    "rel": "related",
                    "href": f"../../themes/{theme}/catalog.json",
                    "type": "application/json",
                    "title": f"Theme: {self.format_string(theme)}",
                },
            )
        return data

    @staticmethod
    def _s3_to_https(s3_url: str) -> str:
        """Convert an s3:// URL to its HTTPS equivalent using AWS virtual-hosted style.

        Example:
            s3://my-bucket/path/to/file → https://my-bucket.s3.amazonaws.com/path/to/file
        """
        without_scheme = s3_url[len("s3://") :]
        bucket, _, key = without_scheme.partition("/")
        return f"https://{bucket}.s3.amazonaws.com/{key}"

    @staticmethod
    def format_string(s: str) -> str:
        # Strip leading/trailing spaces/underscores and replace underscores with spaces
        words = s.strip(" _").replace("_", " ").replace("-", " ").split()
        # Capitalize each word and join them with a space
        return " ".join(word.capitalize() for word in words)

    @staticmethod
    def build_theme(osc_themes: list[str]) -> Theme:
        """Convert each string into a ThemeConcept"""
        concepts = [ThemeConcept(id=theme_str) for theme_str in osc_themes]
        return Theme(concepts=concepts, scheme=OSC_THEME_SCHEME)

    def build_zarr_stac_item(
        self,
        item_config: ItemConfig,
        stac_catalog_s3_root: str,
    ) -> Item:
        """Build a single STAC Item representing the entire Zarr store.

        One item covers the full spatiotemporal extent of the dataset.
        Assets point to the Zarr store and its consolidated metadata.

        Args:
            item_config: object containing `dataset_id` and `item_id`
            stac_catalog_s3_root: S3 root URL where the STAC catalog will be hosted
                (e.g. ``s3://my-bucket/stac/``). Used to build self/root/parent hrefs.

        Returns:
            A :class:`pystac.Item` ready to be serialised to S3.
        """
        self.logger.info(
            f"Building STAC Item {item_config.item_id} "
            f"for collection '{self.collection_id}'."
        )
        dataset = open_dataset(item_config.dataset_id, logger=self.logger)
        spatial_extent = self._get_spatial_extent(dataset)
        temporal_extent = self._get_temporal_extent(dataset)
        general_metadata = self._get_general_metadata(dataset)

        bbox = spatial_extent.bboxes[0]  # [lon_min, lat_min, lon_max, lat_max]
        lon_min, lat_min, lon_max, lat_max = bbox
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [lon_min, lat_min],
                    [lon_max, lat_min],
                    [lon_max, lat_max],
                    [lon_min, lat_max],
                    [lon_min, lat_min],
                ]
            ],
        }

        start_dt, end_dt = temporal_extent.intervals[0]
        # Ensure UTC timezone so ISO strings are STAC-compliant
        if start_dt is not None and start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt is not None and end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        now_iso = datetime.now(timezone.utc).isoformat()
        root = stac_catalog_s3_root.rstrip("/")
        catalog_href = f"{root}/catalog.json"
        item_href = f"{root}/{self.collection_id}/item.json"
        osc_collection_href = (
            "https://esa-earthcode.github.io/open-science-catalog-metadata"
            f"/products/{self.collection_id}/collection.json"
        )

        item = Item(
            id=item_config.item_id,
            geometry=geometry,
            bbox=bbox,
            datetime=None,
            properties={
                "title": self.format_string(item_config.item_id),
                "start_datetime": start_dt.isoformat() if start_dt else None,
                "end_datetime": end_dt.isoformat() if end_dt else None,
                "description": general_metadata.get("description", ""),
                "created": now_iso,
                "updated": now_iso,
            },
        )
        item.collection_id = self.collection_id
        item.set_self_href(item_href)
        item.add_link(
            Link(rel="root", target=catalog_href, media_type="application/json")
        )
        item.add_link(
            Link(rel="parent", target=catalog_href, media_type="application/json")
        )
        item.add_link(
            Link(
                rel="collection",
                target=osc_collection_href,
                media_type="application/json",
                title=self.collection_id,
            )
        )
        access_link = self._build_access_link(item_config)
        item.add_asset(
            "zarr-data",
            Asset(
                href=access_link,
                media_type=ZARR_MEDIA_TYPE,
                title="Zarr Data Store",
                roles=["data"],
            ),
        )
        item.add_asset(
            "zarr-consolidated-metadata",
            Asset(
                href=f"{access_link}/.zmetadata",
                media_type="application/json",
                title="Consolidated Zarr Metadata",
                roles=["metadata"],
            ),
        )
        self.logger.info(f"STAC Item built: {item_href}")
        return item

    def build_zarr_stac_catalog_file_dict(
        self, stac_catalog_s3_root: str
    ) -> dict[str, dict]:
        """Generate the STAC Catalog and Item JSON for the Zarr store.

        The catalog acts as the root for the dataset-level STAC hierarchy
        that lives on S3 alongside the data::

            {stac_catalog_s3_root}/
            ├── catalog.json                   # STAC Catalog (root)
            └── {collection_id}/
                └── item.json       # STAC Item (whole Zarr)

        Args:
            stac_catalog_s3_root: S3 root URL (e.g. ``s3://my-bucket/stac/``).

        Returns:
            ``{s3_path: content_dict}`` for every file to be written to S3.
        """
        self.logger.info(
            f"Building STAC Catalog file dict for collection '{self.collection_id}' "
            f"at root '{stac_catalog_s3_root}'."
        )

        root = stac_catalog_s3_root.rstrip("/")
        catalog_href = f"{root}/catalog.json"
        catalog = Catalog(
            id=f"{self.collection_id}-stac-catalog",
            description=f"STAC Catalog for {self.collection_id}",
        )
        catalog.set_self_href(catalog_href)
        catalog.add_link(
            Link(rel="root", target=catalog_href, media_type="application/json")
        )

        item_config = self.items_config[0]
        item = self.build_zarr_stac_item(item_config, stac_catalog_s3_root)
        catalog.add_link(
            Link(
                rel="item",
                target=f"./{self.collection_id}/items/{item_config.item_id}.json",
                media_type="application/json",
                title=item_config.item_id,
            )
        )
        item_href = f"{root}/{self.collection_id}/items/{item_config.item_id}.json"

        self.logger.info(f"STAC Catalog file dict ready: {catalog_href}, {item_href}")
        return {
            catalog_href: catalog.to_dict(transform_hrefs=False),
            item_href: item.to_dict(transform_hrefs=False),
        }

    # --------------------------------------------------------------------- #
    # PRR (Project Results Repository) style output                         #
    #                                                                       #
    # A self-contained ``Collection -> Item -> Assets`` tree that mirrors   #
    # the ESA EarthCODE PRR tutorial. Emitted alongside (not replacing)     #
    # the plain {collection_id}/items/{item_id}.json under ``{root}/prr/``. #
    # --------------------------------------------------------------------- #

    @staticmethod
    def _get_crs(dataset: xr.Dataset) -> pyproj.CRS:
        """Best-effort EPSG code for the dataset, defaulting to 4326.

        Reads an ``spatial_epsg``/``epsg`` attribute from a ``crs`` or
        ``spatial_ref`` variable when present; otherwise assumes geographic
        WGS 84 (EPSG:4326).
        """
        for var_name in ("spatial_ref", "crs"):
            if var_name in dataset.variables:
                attrs = dataset[var_name].attrs
                try:
                    return pyproj.CRS.from_cf(attrs)
                except pyproj.exceptions.CRSError:
                    for key in ("spatial_epsg", "epsg", "EPSG"):
                        if key in attrs:
                            try:
                                return pyproj.CRS.from_epsg(attrs[key])
                            except (TypeError, ValueError):
                                pass
        return pyproj.CRS.from_epsg(4326)

    def _get_cube_dimensions(self, dataset: xr.Dataset) -> dict[str, dict]:
        """Build the ``cube:dimensions`` object from the dataset coordinates.

        Follows the datacube STAC extension: horizontal spatial dimensions are
        classified by axis (x/y), the ``time`` coordinate becomes a temporal
        dimension, and any remaining index coordinate is emitted as an
        additional dimension.
        """
        crs = self._get_crs(dataset)
        x_names = {"lon", "longitude", "x"}
        y_names = {"lat", "latitude", "y"}
        dimensions: dict[str, dict] = {}
        for name, coord in dataset.coords.items():
            if name not in dataset.dims:
                # Skip non-dimension coordinates (e.g. scalar or auxiliary coords).
                continue
            name = str(name)
            lname = name.lower()
            if lname in x_names:
                dimensions[name] = {
                    "type": "spatial",
                    "axis": "x",
                    "extent": [float(coord.min()), float(coord.max())],
                    "reference_system": crs.to_epsg(),
                }
            elif lname in y_names:
                dimensions[name] = {
                    "type": "spatial",
                    "axis": "y",
                    "extent": [float(coord.min()), float(coord.max())],
                    "reference_system": crs.to_epsg(),
                }
            elif lname == "time":
                time_min = pd.to_datetime(coord.min().values).to_pydatetime()
                time_max = pd.to_datetime(coord.max().values).to_pydatetime()
                dimensions[name] = {
                    "type": "temporal",
                    "extent": [time_min.isoformat(), time_max.isoformat()],
                }
            else:
                try:
                    dimensions[name] = {
                        "type": lname,
                        "extent": [float(coord.min()), float(coord.max())],
                    }
                except (TypeError, ValueError):
                    dimensions[name] = {
                        "type": lname,
                        "values": [str(v) for v in coord.values.tolist()],
                    }
        return dimensions

    @staticmethod
    def _get_cube_variables(dataset: xr.Dataset) -> dict[str, dict]:
        """Build the ``cube:variables`` object from the dataset data variables."""
        skip = {"crs", "spatial_ref"}
        variables: dict[str, dict] = {}
        for name, var in dataset.data_vars.items():
            if name in skip:
                continue
            entry: dict = {
                "type": "data",
                "dimensions": [str(d) for d in var.dims],
            }
            unit = var.attrs.get("units")
            if unit:
                entry["unit"] = unit
            description = var.attrs.get("long_name") or var.attrs.get("description")
            if description:
                entry["description"] = description
            variables[str(name)] = entry
        return variables

    def build_prr_stac_item(self, item_config: ItemConfig) -> Item:
        """Build the single datacube Item for the PRR collection.

        One Item covers the full spatiotemporal extent of the Zarr store. It
        carries the datacube extension (``cube:dimensions`` / ``cube:variables``)
        and two assets pointing at the Zarr store. Structural links
        (root/parent/collection/self) are left for :meth:`save_prr_collection`
        to fill in via ``Collection.add_item`` + ``normalize_hrefs``.
        """
        self.logger.info(
            f"Building PRR STAC Item '{item_config.item_id}' "
            f"for collection '{self.collection_id}'."
        )
        dataset = open_dataset(item_config.dataset_id, logger=self.logger)
        spatial_extent = self._get_spatial_extent(dataset)
        temporal_extent = self._get_temporal_extent(dataset)
        general_metadata = self._get_general_metadata(dataset)

        bbox = spatial_extent.bboxes[0]  # [lon_min, lat_min, lon_max, lat_max]
        lon_min, lat_min, lon_max, lat_max = bbox
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [lon_min, lat_min],
                    [lon_max, lat_min],
                    [lon_max, lat_max],
                    [lon_min, lat_max],
                    [lon_min, lat_min],
                ]
            ],
        }

        start_dt, end_dt = temporal_extent.intervals[0]
        if start_dt is not None and start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt is not None and end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        now_iso = datetime.now(timezone.utc).isoformat()

        item = Item(
            id=item_config.item_id,
            geometry=geometry,
            bbox=bbox,
            datetime=None,
            properties={
                "start_datetime": start_dt.isoformat() if start_dt else None,
                "end_datetime": end_dt.isoformat() if end_dt else None,
                "description": general_metadata.get("description", ""),
                "created": now_iso,
                "updated": now_iso,
                "cube:dimensions": self._get_cube_dimensions(dataset),
                "cube:variables": self._get_cube_variables(dataset),
            },
        )
        item.stac_extensions.append(DATACUBE_SCHEMA_URI)
        # Asset hrefs stay absolute (the Zarr lives on S3); only the structural
        # links become relative when the tree is normalised locally.
        access_link = self._build_access_link(item_config)
        item.add_asset(
            "zarr-data",
            Asset(
                href=access_link,
                media_type=ZARR_MEDIA_TYPE,
                title="Zarr Data Store",
                roles=["data"],
            ),
        )
        item.add_asset(
            "zarr-consolidated-metadata",
            Asset(
                href=f"{access_link}/.zmetadata",
                media_type="application/json",
                title="Consolidated Zarr Metadata",
                roles=["metadata"],
            ),
        )

        self.logger.info(
            f"PRR STAC Item '{item_config.item_id}' built for '{self.collection_id}'."
        )
        return item

    def build_prr_collection(self) -> Collection:
        """Build the PRR parent Collection with its datacube Item(s) attached.

        The Collection carries OSC extension fields (``osc:type``, ``osc:status``,
        ``osc:variables``, ``osc:missions``, ``themes``), a ``cf:parameter`` list
        and ``processing:datetime`` — aligning with the ESA EarthCODE PRR
        endpoint (e.g. ``eoresults.esa.int``). The Item is added as a child, so
        it produces a self-contained tree.
        """
        items = [
            self.build_prr_stac_item(item_config) for item_config in self.items_config
        ]
        spatial_extent = self._union_spatial_extent(items)
        temporal_extent = self._union_temporal_extent(items)
        dataset_ref = open_dataset(self.items_config[0].dataset_id, logger=self.logger)
        variables = self.get_variable_ids(dataset_ref)

        collection = Collection(
            id=self.collection_id,
            description=self.description or "No description provided.",
            extent=Extent(spatial=spatial_extent, temporal=temporal_extent),
            license=self.license_type,
            title=self.collection_id,
        )
        collection.stac_version = "1.0.0"

        osc_extension = OscExtension.add_to(collection)
        osc_extension.osc_project = self.osc_project
        osc_extension.osc_type = "product"
        osc_extension.osc_status = self.osc_status
        osc_extension.osc_region = self.osc_region
        osc_extension.osc_variables = variables
        osc_extension.osc_missions = self.osc_missions
        osc_extension.cf_parameter = self.cf_params or [{"name": self.collection_id}]

        now_iso = datetime.now(timezone.utc).isoformat()
        collection.extra_fields["created"] = now_iso
        collection.extra_fields["updated"] = now_iso

        # Processing extension — the PRR reference collection declares this and
        # exposes 'processing:datetime' (the ingestion/generation timestamp).
        if PROCESSING_SCHEMA_URI not in collection.stac_extensions:
            collection.stac_extensions.append(PROCESSING_SCHEMA_URI)
        collection.extra_fields["processing:datetime"] = now_iso

        if self.osc_themes:
            # Plain dicts (not Theme objects) so the collection serialises with a
            # plain json encoder as well as pystac's own writer.
            collection.extra_fields["themes"] = [
                {
                    "concepts": [{"id": theme} for theme in self.osc_themes],
                    "scheme": OSC_THEME_SCHEME,
                }
            ]

        # ---- Required PRR project-level metadata ----
        # Scientific extension is REQUIRED in the PRR profile's extension list;
        # 'sci:*' values themselves remain optional.
        if SCIENTIFIC_SCHEMA_URI not in collection.stac_extensions:
            collection.stac_extensions.append(SCIENTIFIC_SCHEMA_URI)

        collection.extra_fields["osc:initiative"] = self.osc_initiative
        project_website = (
            self.osc_project_website or self.osc_project_url or self.documentation_link
        )
        if project_website:
            collection.extra_fields["osc:project_website"] = project_website
        project_description = (
            self.osc_project_description
            or self.description
            or "No description provided."
        )
        if project_description:
            collection.extra_fields["osc:project_description"] = project_description
        if self.osc_contract_number:
            collection.extra_fields["osc:contract-number"] = self.osc_contract_number

        # Optional scientific metadata.
        if self.sci_doi:
            collection.extra_fields["sci:doi"] = self.sci_doi
        if self.sci_citation:
            collection.extra_fields["sci:citation"] = self.sci_citation

        # Thumbnail asset (REQUIRED by the PRR spec: an asset named 'thumbnail'
        # with the 'thumbnail' role).
        if self.thumbnail:
            collection.add_asset(
                "thumbnail",
                Asset(
                    href=self.thumbnail,
                    media_type=self._thumbnail_media_type(),
                    title="Collection Thumbnail",
                    roles=["thumbnail"],
                ),
            )

        if self.documentation_link:
            collection.add_link(
                Link(rel="via", target=self.documentation_link, title="Documentation")
            )
        if self.visualisation_link:
            collection.add_link(
                Link(
                    rel="visualisation",
                    target=self.visualisation_link,
                    title="Dataset visualisation",
                )
            )

        try:
            osc_extension.validate_extension()
        except ValueError as e:
            raise ValueError(f"OSC Extension validation failed: {e}")

        self._warn_missing_prr_fields(collection, variables)
        for item in items:
            collection.add_item(item)
        return collection

    def _thumbnail_media_type(self) -> str:
        """Return the thumbnail media type, guessed from the href suffix."""
        if self.thumbnail_media_type:
            return self.thumbnail_media_type
        href = (self.thumbnail or "").lower()
        if href.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if href.endswith(".webp"):
            return "image/webp"
        return "image/png"

    def _warn_missing_prr_fields(
        self, collection: Collection, variables: list[str]
    ) -> None:
        """Log a warning for PRR-required fields that are absent, so the caller
        knows the output is not yet spec-conformant."""
        ef = collection.extra_fields
        missing = []
        if "thumbnail" not in collection.assets:
            missing.append("thumbnail asset")
        if not ef.get("osc:contract-number"):
            missing.append("osc:contract-number")
        if not ef.get("osc:project_website"):
            missing.append("osc:project_website")
        if not ef.get("osc:project_description"):
            missing.append("osc:project_description")
        if not ef.get("themes"):
            missing.append("themes")
        if not variables:
            missing.append("osc:variables")
        if not self.osc_missions:
            missing.append("osc:missions")
        if missing:
            self.logger.warning(
                "PRR collection is missing required field(s): %s. "
                "The collection will not fully conform to the PRR specification "
                "until these are provided in the dataset config.",
                ", ".join(missing),
            )

    def save_prr_collection(self, output_dir: str) -> str:
        """Write the PRR ``Collection -> Item -> Assets`` tree to a local folder.

        Produces a self-contained STAC tree with relative structural links,
        ready to inspect or submit to the ESA EarthCODE PRR endpoint::

            {output_dir}/
            └── {collection_id}/
                └── collection.json            # STAC Collection (root)
                └── items
                    └── {item_id_0}.json       # datacube Item (whole Zarr)
                    └── {item_id_1}.json       # datacube Item (whole Zarr)

        Zarr asset hrefs remain absolute (``s3://…``) since that is where the
        data lives.

        Args:
            output_dir: Local directory to write the collection tree into.

        Returns:
            The ``output_dir`` that was written.
        """
        self.logger.info(
            f"Writing PRR STAC collection for '{self.collection_id}' to "
            f"'{output_dir}'."
        )
        collection = self.build_prr_collection()

        # Set absolute HREFs for writing.
        collection_dir = f"{output_dir}/{self.collection_id}"
        items_dir = f"{collection_dir}/items"
        collection.set_self_href(f"{collection_dir}/collection.json")
        for item in collection.get_items():
            item.set_self_href(f"{items_dir}/{item.id}.json")

        # Write the collection and its children.
        collection.save(catalog_type=CatalogType.SELF_CONTAINED)
        self.logger.info(f"PRR STAC collection written to '{output_dir}'.")
        return output_dir

    def build_dataset_stac_collection(
        self, mode: str, stac_catalog_s3_root: str | None = None
    ) -> Collection:
        """Build an OSC STAC Collection for the dataset.

        Returns:
            A pystac.Collection object.
        """
        try:
            assert len(self.items_config) == 1
            dataset = open_dataset(self.items_config[0].dataset_id, logger=self.logger)
            spatial_extent = self._get_spatial_extent(dataset)
            temporal_extent = self._get_temporal_extent(dataset)
            variables = self.get_variable_ids(dataset)
            general_metadata = self._get_general_metadata(dataset)
        except ValueError as e:
            raise ValueError(f"Metadata extraction failed: {e}")

        # Build base STAC Collection
        collection = Collection(
            id=self.collection_id,
            description=general_metadata.get("description", "No description provided."),
            extent=Extent(spatial=spatial_extent, temporal=temporal_extent),
        )

        # Add OSC extension metadata
        osc_extension = OscExtension.add_to(collection)
        # osc_project and osc_type are fixed constant values
        osc_extension.osc_project = self.osc_project
        osc_extension.osc_type = "product"
        osc_extension.osc_status = self.osc_status
        osc_extension.osc_region = self.osc_region
        osc_extension.osc_variables = variables
        osc_extension.osc_missions = self.osc_missions
        if self.cf_params:
            osc_extension.cf_parameter = self.cf_params
        else:
            osc_extension.cf_parameter = [{"name": self.collection_id}]

        # Add creation and update timestamps for the collection
        now_iso = datetime.now(timezone.utc).isoformat()
        collection.extra_fields["created"] = now_iso
        collection.extra_fields["updated"] = now_iso
        collection.title = self.collection_id

        # Remove any existing root link and re-add it properly
        collection.remove_links("root")
        collection.add_link(
            Link(
                rel="root",
                target="../../catalog.json",
                media_type="application/json",
                title="Open Science Catalog",
            )
        )
        if self.documentation_link:
            collection.add_link(
                Link(rel="via", target=self.documentation_link, title="Documentation")
            )
        if self.visualisation_link:
            collection.add_link(
                Link(
                    rel="visualisation",
                    target=self.visualisation_link,
                    title="Dataset visualisation",
                )
            )
        collection.add_link(
            Link(
                rel="parent",
                target="../catalog.json",
                media_type="application/json",
                title="Products",
            )
        )

        # Add variables ref
        for var in variables:
            collection.add_link(
                Link(
                    rel="related",
                    target=f"../../variables/{var}/catalog.json",
                    media_type="application/json",
                    title="Variable: " + self.format_string(var),
                )
            )

        self_href = (
            "https://esa-earthcode.github.io/"
            f"open-science-catalog-metadata/products/{self.collection_id}/collection.json"
        )
        collection.set_self_href(self_href)

        # align with themes instead of osc:themes
        if self.osc_themes:
            theme_obj = self.build_theme(self.osc_themes)
            collection.extra_fields["themes"] = [theme_obj]

            for theme in self.osc_themes:
                formatted_theme = self.format_string(theme)
                collection.add_link(
                    Link(
                        rel="related",
                        target=f"../../themes/{theme}/catalog.json",
                        media_type="application/json",
                        title=f"Theme: {formatted_theme}",
                    )
                )

        collection.add_link(
            Link(
                rel="related",
                target=f"../../projects/{self.osc_project}/collection.json",
                media_type="application/json",
                title=f"Project: {self.osc_project_title}",
            )
        )

        if mode == "all":
            collection.add_link(
                Link(
                    rel="related",
                    target=f"../../experiments/{self.workflow_id}/record.json",
                    media_type="application/json",
                    title=f"Experiment: {self.workflow_title}",
                )
            )

        collection.license = self.license_type

        # Add links to the S3-hosted STAC catalog following the OSC convention:
        #   via   → STAC browser URL (human-browsable, HTTPS)
        #   child → direct HTTPS URL to catalog.json (machine-readable)
        # The s3:// URL is never used directly in the collection as it fails the
        # products/children.json uri-reference format check.
        if stac_catalog_s3_root:
            catalog_s3 = stac_catalog_s3_root.rstrip("/") + "/catalog.json"
            catalog_https = self._s3_to_https(catalog_s3)
            stac_browser_href = (
                "https://opensciencedata.esa.int/stac-browser/#/external/"
                + catalog_https[len("https://") :]
            )
            collection.add_link(
                Link(
                    rel="via",
                    target=stac_browser_href,
                    title="Access",
                )
            )
            collection.add_link(
                Link(
                    rel="child",
                    target=catalog_https,
                    media_type="application/json",
                    title="Items",
                )
            )

        # Validate OSC extension fields
        try:
            osc_extension.validate_extension()
        except ValueError as e:
            raise ValueError(f"OSC Extension validation failed: {e}")

        return collection
