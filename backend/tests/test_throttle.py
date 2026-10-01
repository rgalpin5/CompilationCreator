import unittest

from app.throttle import FailureThrottle


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class FailureThrottleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.throttle = FailureThrottle(limit=3, window=60, clock=self.clock)

    def test_client_is_paused_at_the_limit_until_its_oldest_failure_expires(self) -> None:
        for _ in range(2):
            self.throttle.record_failure("a")
        self.assertEqual(self.throttle.retry_after("a"), 0)
        self.clock.now += 10
        self.throttle.record_failure("a")
        self.assertEqual(self.throttle.retry_after("a"), 50)
        self.clock.now += 50
        self.assertEqual(self.throttle.retry_after("a"), 0)

    def test_clients_are_counted_separately_and_clear_resets_one(self) -> None:
        for _ in range(3):
            self.throttle.record_failure("a")
        self.assertGreater(self.throttle.retry_after("a"), 0)
        self.assertEqual(self.throttle.retry_after("b"), 0)
        self.throttle.clear("a")
        self.assertEqual(self.throttle.retry_after("a"), 0)

    def test_idle_clients_are_forgotten_once_too_many_are_tracked(self) -> None:
        throttle = FailureThrottle(limit=3, window=60, clock=self.clock, max_clients=2)
        throttle.record_failure("a")
        throttle.record_failure("b")
        self.clock.now += 61
        throttle.record_failure("c")
        self.assertEqual(set(throttle._failures), {"c"})

    def test_least_recently_failed_clients_are_dropped_at_the_cap(self) -> None:
        throttle = FailureThrottle(limit=3, window=60, clock=self.clock, max_clients=2)
        throttle.record_failure("a")
        self.clock.now += 1
        throttle.record_failure("b")
        self.clock.now += 1
        throttle.record_failure("a")
        self.clock.now += 1
        throttle.record_failure("c")
        self.assertEqual(list(throttle._failures), ["a", "c"])
        self.assertEqual(len(throttle._failures["a"]), 2)

    def test_checking_a_client_does_not_store_it(self) -> None:
        self.assertEqual(self.throttle.retry_after("never-failed"), 0)
        self.assertEqual(self.throttle._failures, {})


if __name__ == "__main__":
    unittest.main()
