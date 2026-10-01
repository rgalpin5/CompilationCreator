import threading
import time
import unittest
from unittest.mock import patch

from app.jobs.runner import JobCancelled, Runner, _popen_group_kwargs


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
            jobs._live.add("job-1")
            jobs._pids["job-1"] = {4321}
        with (
            patch("app.jobs.runner.os.name", "nt"),
            patch("app.jobs.runner.subprocess.run") as run,
            patch(
                "app.jobs.runner.os.killpg",
                side_effect=AttributeError("module 'os' has no attribute 'killpg'"),
                create=True,
            ),
        ):
            jobs.cancel("job-1")
        run.assert_called_once()
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ["taskkill", "/F", "/T", "/PID"])
        self.assertEqual(command[4], "4321")

    def test_cancel_all_stops_every_running_export(self) -> None:
        jobs = Runner()
        with jobs._lock:
            jobs._live.update({"job-1", "job-2"})
            jobs._pids["job-1"] = {111, 112}
            jobs._pids["job-2"] = {221}
        with patch("app.jobs.runner._kill_group") as kill:
            jobs.cancel_all()
        self.assertEqual({call.args[0] for call in kill.call_args_list}, {111, 112, 221})
        self.assertTrue(jobs.is_cancelled("job-1"))
        self.assertTrue(jobs.is_cancelled("job-2"))

    def test_cancel_all_leaves_finished_exports_alone(self) -> None:
        jobs = Runner()
        token = jobs.bind("job-1")
        jobs.unbind(token)
        jobs.forget("job-1")
        with patch("app.jobs.runner._kill_group") as kill:
            jobs.cancel_all()
        kill.assert_not_called()
        self.assertEqual(jobs._cancelled, set())

    def test_windows_cancel_all_kills_the_process_tree(self) -> None:
        jobs = Runner()
        with jobs._lock:
            jobs._live.add("job-1")
            jobs._pids["job-1"] = {4321}
        with (
            patch("app.jobs.runner.os.name", "nt"),
            patch("app.jobs.runner.subprocess.run") as run,
        ):
            jobs.cancel_all()
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["taskkill", "/F", "/T", "/PID", "4321"])

    def test_windows_popen_does_not_start_a_unix_session(self) -> None:
        with patch("app.jobs.runner.os.name", "nt"):
            kwargs = _popen_group_kwargs()
        self.assertNotIn("start_new_session", kwargs)
        self.assertIn("creationflags", kwargs)

    def test_forget_clears_a_finished_job(self) -> None:
        jobs = Runner()
        token = jobs.bind("job-1")
        jobs.unbind(token)
        jobs.cancel("job-1")
        self.assertTrue(jobs.is_cancelled("job-1"))
        jobs.forget("job-1")
        self.assertFalse(jobs.is_cancelled("job-1"))

    def test_cancel_ignores_an_export_that_is_not_running(self) -> None:
        jobs = Runner()
        jobs.cancel("never-started")
        token = jobs.bind("job-1")
        jobs.unbind(token)
        jobs.forget("job-1")
        jobs.cancel("job-1")
        self.assertFalse(jobs.is_cancelled("never-started"))
        self.assertFalse(jobs.is_cancelled("job-1"))
        self.assertEqual(jobs._cancelled, set())


if __name__ == "__main__":
    unittest.main()
