#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

from typing import Literal

import pystac
from pystac import Extent, SpatialExtent, TemporalExtent
from pystac.extensions.base import ExtensionManagementMixin, PropertiesExtension

from deep_code.constants import CF_SCHEMA_URI, OSC_SCHEMA_URI, THEMES_SCHEMA_URI


class OscExtension(
    PropertiesExtension, ExtensionManagementMixin[pystac.Item | pystac.Collection]
):
    """Handles the OSC extension for STAC Items and Collections.

    Args:
        obj: The STAC Item or Collection to which the OSC extension is applied.
    """

    name: Literal["osc"] = "osc"

    def __init__(self, obj: pystac.Item | pystac.Collection):
        if isinstance(obj, pystac.Collection):
            self.properties = obj.extra_fields
        else:
            self.properties = obj.properties
        self.obj = obj

    @property
    def osc_type(self) -> str | None:
        return self._get_property("osc:type", str)

    @osc_type.setter
    def osc_type(self, v: str) -> None:
        self._set_property("osc:type", v, pop_if_none=False)

    @property
    def osc_name(self) -> str | None:
        return self._get_property("osc:name", str)

    @osc_name.setter
    def osc_name(self, v: str) -> None:
        self._set_property("osc:name", v, pop_if_none=False)

    @property
    def osc_status(self) -> str | None:
        return self._get_property("osc:status", str)

    @osc_status.setter
    def osc_status(self, value: str) -> None:
        self._set_property("osc:status", value, pop_if_none=False)

    @property
    def osc_project(self) -> str | None:
        return self._get_property("osc:project", str)

    @osc_project.setter
    def osc_project(self, v: str) -> None:
        self._set_property("osc:project", v, pop_if_none=False)

    @property
    def osc_region(self) -> str | None:
        return self._get_property("osc:region", str)

    @osc_region.setter
    def osc_region(self, value: str) -> None:
        self._set_property("osc:region", value, pop_if_none=False)

    @property
    def osc_missions(self) -> list[str] | None:
        return self._get_property("osc:missions", list)

    @osc_missions.setter
    def osc_missions(self, value: list[str]) -> None:
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError("osc:missions must be a list of strings")
        self._set_property("osc:missions", value, pop_if_none=False)

    def set_extent(self, spatial: list[list[float]], temporal: list[list[str]]) -> None:
        self.obj.extent = Extent(SpatialExtent(spatial), TemporalExtent(temporal))

    @property
    def osc_variables(self) -> list[str] | None:
        return self._get_property("osc:variables", list)

    @osc_variables.setter
    def osc_variables(self, v: list[str]) -> None:
        if not isinstance(v, list) or not all(isinstance(item, str) for item in v):
            raise ValueError("osc:variables must be a list of strings")
        self._set_property("osc:variables", v, pop_if_none=False)

    @property
    def keywords(self) -> list[str] | None:
        return self._get_property("keywords", list)

    @keywords.setter
    def keywords(self, value: list[str]) -> None:
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError("keywords must be a list of strings")
        self._set_property("keywords", value, pop_if_none=False)

    @property
    def cf_parameter(self) -> list[dict] | None:
        return self._get_property("cf:parameter", list)

    @cf_parameter.setter
    def cf_parameter(self, value: list[dict]) -> None:
        if not isinstance(value, list) or not all(
            isinstance(item, dict) for item in value
        ):
            raise ValueError("cf:parameter must be a list of dictionaries")
        self._set_property("cf:parameter", value, pop_if_none=False)

    @property
    def created(self) -> str | None:
        return self._get_property("created", str)

    @created.setter
    def created(self, value: str) -> None:
        self._set_property("created", value, pop_if_none=False)

    @property
    def updated(self) -> str | None:
        return self._get_property("updated", str)

    @updated.setter
    def updated(self, value: str) -> None:
        self._set_property("updated", value, pop_if_none=False)

    @classmethod
    def get_schema_uri(cls) -> list[str]:
        return [OSC_SCHEMA_URI, CF_SCHEMA_URI, THEMES_SCHEMA_URI]

    @classmethod
    def ext(
        cls, obj: pystac.Item | pystac.Collection, add_if_missing: bool = False
    ) -> "OscExtension":
        """Returns the OscExtension instance for the given object, adding the extension
        if missing."""
        if cls.has_extension(obj):
            return OscExtension(obj)
        elif add_if_missing:
            return cls.add_to(obj)
        else:
            raise ValueError(
                "OSC extension is not present and add_if_missing is False."
            )

    @classmethod
    def has_extension(cls, obj: pystac.Item | pystac.Collection) -> bool:
        """Checks if all required extensions are present."""
        schema_uris = cls.get_schema_uri()
        if isinstance(schema_uris, list):
            return all(uri in obj.stac_extensions for uri in schema_uris)
        elif isinstance(schema_uris, str):
            return schema_uris in obj.stac_extensions

    @classmethod
    def add_to(cls, obj: pystac.Item | pystac.Collection) -> "OscExtension":
        """Adds the OSC and CF extensions to the object's extensions."""
        schema_uris = cls.get_schema_uri()
        if isinstance(schema_uris, list):  # Handle list of URIs
            for uri in schema_uris:
                if uri not in obj.stac_extensions:
                    obj.stac_extensions.append(uri)
        elif isinstance(schema_uris, str):  # Handle single URI
            if schema_uris not in obj.stac_extensions:
                obj.stac_extensions.append(schema_uris)
        return OscExtension(obj)

    def validate_extension(self) -> None:
        """Validates that all required fields for the OSC extension are set."""
        required_fields = ["osc:type", "osc:project", "osc:status"]
        missing_fields = [
            field
            for field in required_fields
            if self._get_property(field, None) is None
        ]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
