import unittest

from deep_code.constants import OSC_THEME_SCHEME
from deep_code.utils.ogc_record_generator import OSCWorkflowOGCApiRecordGenerator


class TestOSCWorkflowOGCApiRecordGenerator(unittest.TestCase):
    def test_build_contact_objects(self):
        contacts_list = [
            {"name": "Alice", "organization": "Org A", "position": "Researcher"},
            {"name": "Bob", "organization": "Org B", "position": "Developer"},
        ]

        result = OSCWorkflowOGCApiRecordGenerator.build_contact_objects(contacts_list)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Alice")
        self.assertEqual(result[0].organization, "Org A")
        self.assertEqual(result[0].position, "Researcher")
        self.assertEqual(result[1].name, "Bob")
        self.assertEqual(result[1].organization, "Org B")
        self.assertEqual(result[1].position, "Developer")

    def test_build_theme(self):
        osc_themes = ["theme1", "theme2"]

        theme = OSCWorkflowOGCApiRecordGenerator.build_theme(osc_themes)

        self.assertEqual(len(theme.concepts), 2)
        self.assertEqual(theme.concepts[0].id, "theme1")
        self.assertEqual(theme.concepts[1].id, "theme2")
        self.assertEqual(theme.scheme, OSC_THEME_SCHEME)

    def test_build_record_properties(self):
        generator = OSCWorkflowOGCApiRecordGenerator()
        properties = {
            "title": "Test Workflow",
            "description": "A test description",
            "themes": ["theme1"],
            "jupyter_kernel_info": {
                "name": "deepesdl-xcube-1.7.1",
                "python_version": 3.11,
                "env_file": "https://git/env.yml",
            },
        }
        contacts = [
            {"name": "Alice", "organization": "Org A", "position": "Researcher"}
        ]

        record_properties = generator.build_record_properties(properties, contacts)

        self.assertEqual(record_properties.title, "Test Workflow")
        self.assertEqual(record_properties.description, "A test description")
        self.assertEqual(len(record_properties.contacts), 1)
        self.assertEqual(record_properties.contacts[0].name, "Alice")
        self.assertEqual(len(record_properties.themes), 1)
        self.assertEqual(record_properties.themes[0].concepts[0].id, "theme1")
        self.assertEqual(record_properties.type, "workflow")
        self.assertTrue("created" in record_properties.__dict__)
        self.assertTrue("updated" in record_properties.__dict__)
