#!/usr/bin/env python3

# Copyright (c) 2025 by Brockmann Consult GmbH
# Permissions are hereby granted under the terms of the MIT License:
# https://opensource.org/licenses/MIT.

from datetime import datetime, timezone

from deep_code.constants import OSC_THEME_SCHEME
from deep_code.utils.ogc_api_record import (
    Contact,
    RecordProperties,
    Theme,
    ThemeConcept,
)


class OSCWorkflowOGCApiRecordGenerator:
    """Generates OGC API record for a workflow
    """

    @staticmethod
    def build_contact_objects(contacts_list: list[dict]) -> list[Contact]:
        """Build a list of Contact objects from a list of contact dictionaries.
            Uses the inherited MappingConstructible logic to parse each dict.

            Args:
                contacts_list: A list of dictionaries, each containing contact information.

            Returns:
                A list of Contact instances.
            """
        return [Contact.from_value(cdict) for cdict in contacts_list]

    @staticmethod
    def build_theme(osc_themes: list[str]) -> Theme:
        """Convert each string into a ThemeConcept
        """
        concepts = [ThemeConcept(id=theme_str) for theme_str in osc_themes]
        return Theme(concepts=concepts, scheme=OSC_THEME_SCHEME)

    def build_record_properties(
        self, properties: dict, contacts: list
    ) -> RecordProperties:
        """Build a RecordProperties object from a properties dictionary.

        Args:
            properties: A dictionary containing properties (e.g., title, description, themes).
            contacts: A list of contact dictionaries.

        Returns:
            A RecordProperties object.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        properties.update({"created": now_iso})
        properties.update({"updated": now_iso})

        themes_list = properties.get("themes", [])

        properties.update({"contacts": self.build_contact_objects(contacts)})

        if themes_list:
            theme_obj = self.build_theme(themes_list)
            properties.update({"themes": [theme_obj]})

        properties.setdefault("type", "workflow")
        properties.setdefault("osc_project", "deep-earth-system-data-lab")

        return RecordProperties.from_value(properties)
