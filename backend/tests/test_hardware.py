import unittest
from unittest.mock import patch

from app.hardware import download_workers, fragment_connections, prepare_workers


class HardwareBudgetTests(unittest.TestCase):
    def test_downloads_never_exceed_four_or_the_cpu_count(self) -> None:
        with patch("app.hardware.available_cpus", return_value=32):
            self.assertEqual(download_workers(10), 4)
        with patch("app.hardware.available_cpus", return_value=2):
            self.assertEqual(download_workers(10), 2)

    def test_picture_encodes_follow_half_the_cores(self) -> None:
        with patch("app.hardware.available_cpus", return_value=8):
            self.assertEqual(prepare_workers(10, encodes_video=True), 4)
        with patch("app.hardware.available_cpus", return_value=4):
            self.assertEqual(prepare_workers(10, encodes_video=True), 2)
        with patch("app.hardware.available_cpus", return_value=2):
            self.assertEqual(prepare_workers(10, encodes_video=True), 1)

    def test_fragment_connections_stay_between_four_and_sixteen(self) -> None:
        with patch("app.hardware.available_cpus", return_value=8):
            self.assertEqual(fragment_connections(), 16)
        with patch("app.hardware.available_cpus", return_value=2):
            self.assertEqual(fragment_connections(), 4)
        with patch("app.hardware.available_cpus", return_value=64):
            self.assertEqual(fragment_connections(), 16)


class DesktopPathTests(unittest.TestCase):
    def test_source_checkout_serves_the_frontend_export(self) -> None:
        from app.desktop.paths import static_dir

        ui = static_dir()
        self.assertEqual(ui.name, "out")
        self.assertEqual(ui.parent.name, "frontend")

    def test_packaging_can_import_main(self) -> None:
        from app.desktop import main

        self.assertTrue(callable(main))
