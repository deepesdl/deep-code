import unittest

from pystac import Collection, Extent, SpatialExtent, TemporalExtent

from deep_code.utils.osc_extension import OscExtension


class TestOscExtension(unittest.TestCase):
    def setUp(self):
        """Set up a test Collection object and attach the OscExtension."""
        self.collection = Collection(
            id="test-collection",
            description="Test collection for unit tests",
            extent=Extent(
                spatial=SpatialExtent([[-180, -90, 180, 90]]),
                temporal=TemporalExtent(
                    [["2022-01-01T00:00:00Z", "2023-01-01T00:00:00Z"]]
                ),
            ),
            stac_extensions=[],
        )
        OscExtension.add_to(self.collection)

    def test_osc_status(self):
        """Test the osc:status property."""
        extension = OscExtension.ext(self.collection)
        extension.osc_status = "ongoing"
        self.assertEqual(extension.osc_status, "ongoing")

    def test_osc_region(self):
        """Test the osc:region property."""
        extension = OscExtension.ext(self.collection)
        extension.osc_region = "Mediterranean region"
        self.assertEqual(extension.osc_region, "Mediterranean region")

    def test_osc_themes(self):
        """Test the osc:themes property."""
        extension = OscExtension.ext(self.collection)
        extension.osc_themes = ["land", "ocean"]
        self.assertEqual(extension.osc_themes, ["land", "ocean"])

    def test_osc_missions(self):
        """Test the osc:missions property."""
        extension = OscExtension.ext(self.collection)
        extension.osc_missions = ["mission1", "mission2"]
        self.assertEqual(extension.osc_missions, ["mission1", "mission2"])

    def test_keywords(self):
        """Test the keywords property."""
        extension = OscExtension.ext(self.collection)
        extension.keywords = ["Hydrology", "Remote Sensing"]
        self.assertEqual(extension.keywords, ["Hydrology", "Remote Sensing"])

    def test_cf_parameters(self):
        """Test the cf:parameter property."""
        extension = OscExtension.ext(self.collection)
        extension.cf_parameter = [{"name": "hydrology-4D"}]
        self.assertEqual(extension.cf_parameter, [{"name": "hydrology-4D"}])

    def test_created_updated(self):
        """Test the created and updated properties."""
        extension = OscExtension.ext(self.collection)
        extension.created = "2023-12-21T11:50:17Z"
        extension.updated = "2023-12-21T11:50:17Z"
        self.assertEqual(extension.created, "2023-12-21T11:50:17Z")
        self.assertEqual(extension.updated, "2023-12-21T11:50:17Z")

    def test_set_extent(self):
        """Test setting spatial and temporal extent."""
        extension = OscExtension.ext(self.collection)
        spatial = [[-5.7, 28.3, 37.7, 48.1]]
        temporal = [["2014-12-31T12:00:00Z", "2022-10-06T12:00:00Z"]]
        extension.set_extent(spatial, temporal)

        self.assertEqual(self.collection.extent.spatial.bboxes, spatial)
        self.assertEqual(self.collection.extent.temporal.intervals, temporal)

    def test_validation_success(self):
        """Test validation with all required fields."""
        extension = OscExtension.ext(self.collection)
        extension.osc_type = "product"
        extension.osc_project = "test-project"
        extension.osc_status = "ongoing"
        extension.validate_extension()  # Should not raise an exception

    def test_add_osc_extension(self):
        osc_ext = OscExtension.add_to(self.collection)
        self.assertEqual(OscExtension.get_schema_uri(), self.collection.stac_extensions)
        self.assertIsInstance(osc_ext, OscExtension)

    def test_has_extension(self):
        self.collection.stac_extensions = []
        self.assertFalse(OscExtension.has_extension(self.collection))
        OscExtension.add_to(self.collection)
        self.assertTrue(OscExtension.has_extension(self.collection))

    def test_set_and_get_properties(self):
        osc_ext = OscExtension.add_to(self.collection)
        osc_ext.osc_type = "example-type"
        osc_ext.osc_project = "example-project"
        osc_ext.osc_product = "example-product"
        osc_ext.osc_theme = ["example-theme"]
        osc_ext.osc_variables = ["var1", "var2", "var3"]

        self.assertEqual(osc_ext.osc_type, "example-type")
        self.assertEqual(osc_ext.osc_project, "example-project")
        self.assertEqual(osc_ext.osc_product, "example-product")
        self.assertEqual(osc_ext.osc_theme, ["example-theme"])
        self.assertListEqual(osc_ext.osc_variables, ["var1", "var2", "var3"])

    def test_validation_missing_fields(self):
        """Test validation with missing required fields."""
        extension = OscExtension.ext(self.collection)
        with self.assertRaises(ValueError) as context:
            extension.validate_extension()
        self.assertIn("Missing required fields", str(context.exception))
        self.assertIn("osc:type", str(context.exception))
