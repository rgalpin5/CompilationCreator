import threading
import time
import unittest

from app.services.runner import JobCancelled, Runner


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


if __name__ == "__main__":
    unittest.main()
