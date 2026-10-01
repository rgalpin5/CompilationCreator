import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.hardware import (
    available_cpus,
    download_workers,
    fragment_connections,
    prepare_workers,
)


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

    def test_empty_task_lists_still_get_one_worker(self) -> None:
        self.assertEqual(download_workers(0), 1)
        self.assertEqual(prepare_workers(0, encodes_video=False), 1)

    def test_stream_copy_prep_stays_at_four(self) -> None:
        with patch("app.hardware.available_cpus", return_value=32):
            self.assertEqual(prepare_workers(10, encodes_video=False), 4)


class AvailableCpuTests(unittest.TestCase):
    def test_affinity_reports_the_container_limit(self) -> None:
        with (
            patch("app.hardware.os.sched_getaffinity", lambda _pid: {0, 1, 2}, create=True),
            patch("app.hardware.os.cpu_count", return_value=64),
        ):
            self.assertEqual(available_cpus(), 3)

    def test_affinity_failure_falls_back_to_cpu_count(self) -> None:
        def _denied(_pid: int) -> set[int]:
            raise OSError("not permitted")

        with (
            patch("app.hardware.os.sched_getaffinity", _denied, create=True),
            patch("app.hardware.os.cpu_count", return_value=6),
        ):
            self.assertEqual(available_cpus(), 6)

    def test_without_affinity_uses_cpu_count(self) -> None:
        with (
            patch("app.hardware.os", SimpleNamespace(cpu_count=lambda: 12)),
        ):
            self.assertEqual(available_cpus(), 12)

    def test_unknown_cpu_count_is_one(self) -> None:
        with patch("app.hardware.os", SimpleNamespace(cpu_count=lambda: None)):
            self.assertEqual(available_cpus(), 1)


class DesktopPathTests(unittest.TestCase):
    def test_source_checkout_serves_the_frontend_export(self) -> None:
        from app.desktop.paths import static_dir

        ui = static_dir()
        self.assertEqual(ui.name, "out")
        self.assertEqual(ui.parent.name, "frontend")

    def test_packaging_can_import_main(self) -> None:
        from app.desktop import main

        self.assertTrue(callable(main))
