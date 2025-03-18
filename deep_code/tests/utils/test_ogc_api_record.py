import unittest

from deep_code.constants import OGC_API_RECORD_SPEC
from deep_code.utils.ogc_api_record import (
    Contact,
    ExperimentAsOgcRecord,
    JupyterKernelInfo,
    LinksBuilder,
    RecordProperties,
    Theme,
    ThemeConcept,
    WorkflowAsOgcRecord,
)


class TestContact(unittest.TestCase):
    def test_contact_initialization(self):
        contact = Contact(
            name="John Doe",
            organization="DeepESDL",
            position="Researcher",
            links=[{"href": "https://example.com"}],
            contactInstructions="Contact via email",
            roles=["principal investigator"],
        )

        self.assertEqual(contact.name, "John Doe")
        self.assertEqual(contact.organization, "DeepESDL")
        self.assertEqual(contact.position, "Researcher")
        self.assertEqual(contact.links, [{"href": "https://example.com"}])
        self.assertEqual(contact.contactInstructions, "Contact via email")
        self.assertEqual(contact.roles, ["principal investigator"])

    def test_contact_default_values(self):
        contact = Contact(name="Jane Doe", organization="DeepESDL")

        self.assertEqual(contact.position, "")
        self.assertEqual(contact.links, [])
        self.assertEqual(contact.contactInstructions, "")
        self.assertEqual(contact.roles, ["principal investigator"])


class TestThemeConcept(unittest.TestCase):
    def test_theme_concept_initialization(self):
        theme_concept = ThemeConcept(id="climate")

        self.assertEqual(theme_concept.id, "climate")


class TestTheme(unittest.TestCase):
    def test_theme_initialization(self):
        theme_concept = ThemeConcept(id="climate")
        theme = Theme(concepts=[theme_concept], scheme="https://example.com")

        self.assertEqual(theme.concepts, [theme_concept])
        self.assertEqual(theme.scheme, "https://example.com")


class TestJupyterKernelInfo(unittest.TestCase):
    def test_jupyter_kernel_info_initialization(self):
        kernel_info = JupyterKernelInfo(
            name="python3", python_version=3.9, env_file="environment.yml"
        )

        self.assertEqual(kernel_info.name, "python3")
        self.assertEqual(kernel_info.python_version, 3.9)
        self.assertEqual(kernel_info.env_file, "environment.yml")


class TestRecordProperties(unittest.TestCase):
    def test_record_properties_initialization(self):
        kernel_info = JupyterKernelInfo(
            name="python3", python_version=3.9, env_file="environment.yml"
        )
        contact = Contact(name="John Doe", organization="DeepESDL")
        theme = Theme(
            concepts=[ThemeConcept(id="climate")], scheme="https://example.com"
        )

        record_properties = RecordProperties(
            created="2023-01-01",
            type="workflow",
            title="Test Workflow",
            description="A test workflow",
            jupyter_kernel_info=kernel_info,
            osc_project="DeepESDL",
            osc_workflow="test-workflow",
            updated="2023-01-02",
            contacts=[contact],
            themes=[theme],
            keywords=["test", "workflow"],
            formats=[{"type": "application/json"}],
            license="MIT",
        )

        self.assertEqual(record_properties.created, "2023-01-01")
        self.assertEqual(record_properties.updated, "2023-01-02")
        self.assertEqual(record_properties.type, "workflow")
        self.assertEqual(record_properties.title, "Test Workflow")
        self.assertEqual(record_properties.description, "A test workflow")
        self.assertEqual(record_properties.jupyter_kernel_info, kernel_info)
        self.assertEqual(record_properties.osc_project, "DeepESDL")
        self.assertEqual(record_properties.osc_workflow, "test-workflow")
        self.assertEqual(record_properties.keywords, ["test", "workflow"])
        self.assertEqual(record_properties.contacts, [contact])
        self.assertEqual(record_properties.themes, [theme])
        self.assertEqual(record_properties.formats, [{"type": "application/json"}])
        self.assertEqual(record_properties.license, "MIT")

    def test_record_properties_to_dict(self):
        kernel_info = JupyterKernelInfo(
            name="python3", python_version=3.9, env_file="environment.yml"
        )
        record_properties = RecordProperties(
            created="2023-01-01",
            type="workflow",
            title="Test Workflow",
            description="A test workflow",
            jupyter_kernel_info=kernel_info,
            osc_project="DeepESDL",
            osc_workflow="test-workflow",
        )

        result = record_properties.to_dict()

        self.assertEqual(result["created"], "2023-01-01")
        self.assertEqual(result["type"], "workflow")
        self.assertEqual(result["title"], "Test Workflow")
        self.assertEqual(result["description"], "A test workflow")
        self.assertEqual(result["jupyter_kernel_info"], kernel_info.to_dict())
        self.assertEqual(result["osc:project"], "DeepESDL")
        self.assertEqual(result["osc:workflow"], "test-workflow")
        self.assertNotIn("osc_project", result)
        self.assertNotIn("osc_workflow", result)


class TestLinksBuilder(unittest.TestCase):
    def test_build_theme_links_for_records(self):
        links_builder = LinksBuilder(themes=["climate", "ocean"])
        theme_links = links_builder.build_theme_links_for_records()

        expected_links = [
            {
                "rel": "related",
                "href": "../../themes/climate/catalog.json",
                "type": "application/json",
                "title": "Theme: Climate",
            },
            {
                "rel": "related",
                "href": "../../themes/ocean/catalog.json",
                "type": "application/json",
                "title": "Theme: Ocean",
            },
        ]

        self.assertEqual(theme_links, expected_links)

    def test_build_link_to_dataset(self):
        link = LinksBuilder.build_link_to_dataset("test-collection")

        expected_link = [
            {
                "rel": "child",
                "href": "../../products/test-collection/collection.json",
                "type": "application/json",
                "title": "test-collection",
            }
        ]

        self.assertEqual(link, expected_link)


class TestWorkflowAsOgcRecord(unittest.TestCase):
    def test_workflow_as_ogc_record_initialization(self):
        kernel_info = JupyterKernelInfo(
            name="python3", python_version=3.9, env_file="environment.yml"
        )
        record_properties = RecordProperties(
            created="2023-01-01",
            type="workflow",
            title="Test Workflow",
            description="A test workflow",
            jupyter_kernel_info=kernel_info,
            osc_project="DeepESDL",
        )

        workflow_record = WorkflowAsOgcRecord(
            id="test-workflow",
            type="workflow",
            title="Test Workflow",
            jupyter_notebook_url="https://example.com/notebook.ipynb",
            properties=record_properties,
            links=[{"rel": "self", "href": "https://example.com"}],
        )

        self.assertEqual(workflow_record.id, "test-workflow")
        self.assertEqual(workflow_record.type, "workflow")
        self.assertEqual(workflow_record.title, "Test Workflow")
        self.assertEqual(
            workflow_record.jupyter_notebook_url, "https://example.com/notebook.ipynb"
        )
        self.assertEqual(workflow_record.properties, record_properties)
        self.assertEqual(workflow_record.conformsTo, [OGC_API_RECORD_SPEC])
        self.assertEqual(workflow_record.links[0]["rel"], "root")
        self.assertEqual(workflow_record.links[-1]["rel"], "self")


class TestExperimentAsOgcRecord(unittest.TestCase):
    def test_experiment_as_ogc_record_initialization(self):
        kernel_info = JupyterKernelInfo(
            name="python3", python_version=3.12, env_file="environment.yml"
        )
        record_properties = RecordProperties(
            created="2023-01-01",
            type="experiment",
            title="Test Experiment",
            description="A test experiment",
            jupyter_kernel_info=kernel_info,
            osc_project="DeepESDL",
        )

        experiment_record = ExperimentAsOgcRecord(
            id="test-experiment",
            title="Test Experiment",
            type="experiment",
            jupyter_notebook_url="https://example.com/notebook.ipynb",
            collection_id="test-collection",
            properties=record_properties,
            links=[{"rel": "self", "href": "https://example.com"}],
        )

        self.assertEqual(experiment_record.id, "test-experiment")
        self.assertEqual(experiment_record.title, "Test Experiment")
        self.assertEqual(experiment_record.type, "experiment")
        self.assertEqual(
            experiment_record.jupyter_notebook_url, "https://example.com/notebook.ipynb"
        )
        self.assertEqual(experiment_record.collection_id, "test-collection")
        self.assertEqual(experiment_record.properties, record_properties)
        self.assertEqual(experiment_record.conformsTo, [OGC_API_RECORD_SPEC])
        self.assertEqual(experiment_record.links[0]["rel"], "root")
        self.assertEqual(experiment_record.links[-1]["rel"], "self")
