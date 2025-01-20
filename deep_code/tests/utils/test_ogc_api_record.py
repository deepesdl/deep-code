import unittest

from deep_code.constants import OGC_API_RECORD_SPEC
from deep_code.utils.ogc_api_record import (Contact, JupyterKernelInfo,
                                            OgcRecord, RecordProperties, Theme,
                                            ThemeConcept)


class TestClasses(unittest.TestCase):

    def test_contact_initialization(self):
        contact = Contact(
            name="Person-X",
            organization="Organization X",
            position="Researcher",
            links=[{"url": "http://example.com", "type": "website"}],
            contactInstructions="Contact via email",
            roles=["developer", "reviewer"]
        )

        self.assertEqual(contact.name, "Person-X")
        self.assertEqual(contact.organization, "Organization X")
        self.assertEqual(contact.position, "Researcher")
        self.assertEqual(len(contact.links), 1)
        self.assertEqual(contact.contactInstructions, "Contact via email")
        self.assertIn("developer", contact.roles)

    def test_theme_concept_initialization(self):
        theme_concept = ThemeConcept(id="concept1")
        self.assertEqual(theme_concept.id, "concept1")

    def test_theme_initialization(self):
        theme_concepts = [ThemeConcept(id="concept1"), ThemeConcept(id="concept2")]
        theme = Theme(concepts=theme_concepts, scheme="http://example.com/scheme")

        self.assertEqual(len(theme.concepts), 2)
        self.assertEqual(theme.scheme, "http://example.com/scheme")

    def test_jupyter_kernel_info_initialization(self):
        kernel_info = JupyterKernelInfo(name="Python", python_version=3.9, env_file="env.yml")

        self.assertEqual(kernel_info.name, "Python")
        self.assertEqual(kernel_info.python_version, 3.9)
        self.assertEqual(kernel_info.env_file, "env.yml")

    def test_record_properties_initialization(self):
        kernel_info = JupyterKernelInfo(name="Python", python_version=3.9, env_file="env.yml")
        contacts = [Contact(name="Jane Doe", organization="Org Y")]
        themes = [Theme(concepts=[ThemeConcept(id="concept1")], scheme="scheme1")]

        record_properties = RecordProperties(
            created="2025-01-01",
            type="dataset",
            title="Sample Dataset",
            description="A sample dataset",
            jupyter_kernel_info=kernel_info,
            updated="2025-01-02",
            contacts=contacts,
            themes=themes,
            keywords=["sample", "test"],
            formats=[{"format": "JSON"}],
            license="CC-BY"
        )

        self.assertEqual(record_properties.created, "2025-01-01")
        self.assertEqual(record_properties.updated, "2025-01-02")
        self.assertEqual(record_properties.type, "dataset")
        self.assertEqual(record_properties.title, "Sample Dataset")
        self.assertEqual(record_properties.description, "A sample dataset")
        self.assertEqual(record_properties.jupyter_kernel_info.name, "Python")
        self.assertEqual(len(record_properties.contacts), 1)
        self.assertEqual(len(record_properties.themes), 1)
        self.assertIn("sample", record_properties.keywords)
        self.assertEqual(record_properties.license, "CC-BY")

    def test_ogc_record_initialization(self):
        kernel_info = JupyterKernelInfo(name="Python", python_version=3.9, env_file="env.yml")
        properties = RecordProperties(
            created="2025-01-01",
            type="dataset",
            title="Sample Dataset",
            description="A sample dataset",
            jupyter_kernel_info=kernel_info
        )

        ogc_record = OgcRecord(
            id="record1",
            type="Feature",
            time={"start": "2025-01-01T00:00:00Z", "end": "2025-01-02T00:00:00Z"},
            properties=properties,
            links=[{"href": "http://example.com", "rel": "self"}],
            linkTemplates=[{"template": "http://example.com/{id}"}]
        )

        self.assertEqual(ogc_record.id, "record1")
        self.assertEqual(ogc_record.type, "Feature")
        self.assertEqual(ogc_record.time["start"], "2025-01-01T00:00:00Z")
        self.assertEqual(ogc_record.properties.title, "Sample Dataset")
        self.assertEqual(len(ogc_record.links), 1)
        self.assertEqual(ogc_record.linkTemplates[0]["template"], "http://example.com/{id}")
        self.assertEqual(ogc_record.conformsTo[0], OGC_API_RECORD_SPEC)

