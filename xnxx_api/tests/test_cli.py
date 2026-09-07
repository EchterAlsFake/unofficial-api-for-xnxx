import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from xnxx_api.api import create_parser, run_main


class TestCLI(unittest.IsolatedAsyncioTestCase):
    def test_parser_defaults(self):
        parser = create_parser()
        args = parser.parse_args(["--output", "/tmp/out"])
        self.assertEqual(args.quality, "best")
        self.assertEqual(args.no_title, "False")
        self.assertEqual(args.output, "/tmp/out")
        self.assertIsNone(args.download)
        self.assertIsNone(args.file)

    def test_parser_custom_args(self):
        parser = create_parser()
        args = parser.parse_args([
            "--download", "https://xnxx.com/video-123/test",
            "--output", "/tmp/out",
            "--quality", "worst",
            "--no-title", "True"
        ])
        self.assertEqual(args.download, "https://xnxx.com/video-123/test")
        self.assertEqual(args.output, "/tmp/out")
        self.assertEqual(args.quality, "worst")
        self.assertEqual(args.no_title, "True")

    def test_parser_no_title_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--output", "/tmp/out", "--no-title"])
        self.assertEqual(args.no_title, "True")

    async def test_run_main_download(self):
        mock_video = MagicMock()
        mock_video.title = "Sample Video"
        mock_video.download = AsyncMock()

        mock_client = MagicMock()
        mock_client.get_video = AsyncMock(return_value=mock_video)

        with patch("xnxx_api.api.Client", return_value=mock_client):
            await run_main(["--download", "https://xnxx.com/video-123/test", "--output", "/tmp/out"])

        mock_client.get_video.assert_awaited_once_with("https://xnxx.com/video-123/test", load_html=True)
        mock_video.download.assert_awaited_once()

    async def test_run_main_file(self):
        mock_video = MagicMock()
        mock_video.title = "Sample Video"
        mock_video.download = AsyncMock()

        mock_client = MagicMock()
        mock_client.get_video = AsyncMock(return_value=mock_video)

        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("https://xnxx.com/1\nhttps://xnxx.com/2\n")
            f.flush()
            temp_name = f.name

        try:
            with patch("xnxx_api.api.Client", return_value=mock_client):
                await run_main(["--file", temp_name, "--output", "/tmp/out"])

            self.assertEqual(mock_client.get_video.await_count, 2)
            self.assertEqual(mock_video.download.await_count, 2)
        finally:
            if os.path.exists(temp_name):
                os.remove(temp_name)

    async def test_real_download(self):
        """Integration test: verifies real video download via CLI."""
        url = "https://www.xnxx.com/video-1b9bufc9/die_zierliche_stieftochter_passt_kaum_in_den_mund_ihres_stiefvaters"
        with tempfile.TemporaryDirectory() as tmp_dir:
            await run_main(["--download", url, "--output", tmp_dir, "--quality", "worst"])
            files = [f for f in os.listdir(tmp_dir) if not f.endswith(".tmp")]
            self.assertTrue(len(files) > 0, "Expected downloaded video file in output directory")


if __name__ == "__main__":
    unittest.main()
