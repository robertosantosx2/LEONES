import unittest

from contract import AdapterContext, lifecycle


class FakeAdapter:
    name = "fake"

    def __init__(self):
        self.calls = []

    def _ok(self, operation, context):
        self.calls.append(operation)
        from contract import AdapterResult
        return AdapterResult(self.name, operation, "ok")

    detect = lambda self, c: self._ok("detect", c)
    select = lambda self, c: self._ok("select", c)
    pin = lambda self, c: self._ok("pin", c)
    install = lambda self, c: self._ok("install", c)
    verify = lambda self, c: self._ok("verify", c)
    measure = lambda self, c: self._ok("measure", c)
    report = lambda self, c: self._ok("report", c)
    cleanup = lambda self, c: self._ok("cleanup", c)


class ContractTests(unittest.TestCase):
    def test_lifecycle_order(self):
        adapter = FakeAdapter()
        results = lifecycle(adapter, AdapterContext(target="test", dry_run=True))
        self.assertEqual([result.operation for result in results], [
            "detect", "select", "pin", "install", "verify", "measure", "report", "cleanup"
        ])
        self.assertEqual(adapter.calls, [
            "detect", "select", "pin", "install", "verify", "measure", "report", "cleanup"
        ])

    def test_lifecycle_stops_on_failure(self):
        class Failing(FakeAdapter):
            def verify(self, context):
                from contract import AdapterResult
                return AdapterResult(self.name, "verify", "failed")

        results = lifecycle(Failing(), AdapterContext(target="test"))
        self.assertEqual(results[-1].operation, "verify")
        self.assertEqual(results[-1].status, "failed")


if __name__ == "__main__":
    unittest.main()
