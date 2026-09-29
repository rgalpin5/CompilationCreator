import threading
import time
import unittest
from unittest.mock import patch

from app.services.runner import JobCancelled, Runner, _popen_group_kwargs


class CancelTests(unittest.TestCase):
    def test_cancel_stops_a_running_process(self) -> None:
        jobs = Runner()
        token = jobs.bind("job-1")
        try:
            def stop() -> None:
                time.sleep(0.3)
                jobs.cancel("job-1")

            threading.Thread(target=stop).start()
            started = time.time()
            with self.assertRaises(JobCancelled):
                jobs.run(["sleep", "30"])
            self.assertLess(time.time() - started, 5)
        finally:
            jobs.unbind(token)

    def test_windows_cancel_kills_the_process_tree(self) -> None:
        jobs = Runner()
        with jobs._lock:
            jobs._pids["job-1"] = {4321}
        with (
            patch("app.services.runner.os.name", "nt"),
            patch("app.services.runner.subprocess.run") as run,
            patch(
                "app.services.runner.os.killpg",
                side_effect=AttributeError("module 'os' has no attribute 'killpg'"),
                create=True,
            ),
        ):
            jobs.cancel("job-1")
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["taskkill", "/F", "/T", "/PID"])
        self.assertEqual(command[4], "4321")

    def test_windows_popen_does_not_start_a_unix_session(self) -> None:
        with patch("app.services.runner.os.name", "nt"):
            kwargs = _popen_group_kwargs()
        self.assertNotIn("start_new_session", kwargs)
        self.assertIn("creationflags", kwargs)


if __name__ == "__main__":
    unittest.main()
