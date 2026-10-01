import os
import signal
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import dev


@unittest.skipIf(sys.platform == "win32", "process groups are POSIX-only")
class StopTests(unittest.TestCase):
    def test_spawn_starts_a_new_session(self) -> None:
        with patch("dev.subprocess.Popen") as popen:
            dev._spawn(["npm", "run", "dev"], cwd=Path("."))
        self.assertIs(popen.call_args.kwargs.get("start_new_session"), True)

    def test_stop_signals_the_whole_group(self) -> None:
        process = MagicMock(pid=4321)
        with patch("dev.os.killpg", side_effect=[None, ProcessLookupError()]) as killpg:
            dev._stop(process)
        self.assertEqual(killpg.call_args_list, [call(4321, signal.SIGTERM), call(4321, 0)])

    def test_stop_kills_a_group_that_ignores_sigterm(self) -> None:
        process = MagicMock(pid=4321)
        with patch("dev.os.killpg") as killpg:
            dev._stop(process, timeout=0)
        self.assertEqual(killpg.call_args_list[0], call(4321, signal.SIGTERM))
        self.assertEqual(killpg.call_args_list[-1], call(4321, signal.SIGKILL))

    def test_stop_ends_a_grandchild_too(self) -> None:
        # The shell stands in for npm and the sleep for the node server it starts.
        process = dev._spawn(["sh", "-c", "sleep 30 & wait"], cwd=Path("."))
        try:
            time.sleep(0.3)
            dev._stop(process, timeout=3)
            self.assertIsNotNone(process.poll())
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
