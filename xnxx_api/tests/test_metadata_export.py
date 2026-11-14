import unittest

from xnxx_api.api import Video


class MetadataExportTests(unittest.TestCase):
    def test_upload_date_is_qualified_and_comment_date_is_ignored(self):
        fields = Video._extract_html('<!-- dispo - Thursday, 01 October 2026 12:00:00 +0000 Loaded ! -->')
        self.assertIsNone(fields["publish_date"])
        fields = Video._extract_html('<script type="application/ld+json">{"@type":"VideoObject","uploadDate":"2026-10-01"}</script>')
        self.assertEqual(fields["publish_date_source"], "uploadDate")
        self.assertEqual(fields["publish_date"], "2026-10-01")
