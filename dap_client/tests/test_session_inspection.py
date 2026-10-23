"""Tests that the DAP client session exposes real inspection requests."""

from dap_client.core.session import DAPSession


class StubConnection:
    def __init__(self):
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        return {"body_for": request.command}


def test_inspection_methods_send_real_dap_requests():
    connection = StubConnection()
    session = DAPSession(connection=connection)

    assert session.get_threads() == {"body_for": "threads"}
    assert session.get_stacktrace(7) == {"body_for": "stackTrace"}
    assert session.get_scopes(3) == {"body_for": "scopes"}
    assert session.get_variables(11) == {"body_for": "variables"}
    assert session.evaluate("a + 1", frame_id=2) == {"body_for": "evaluate"}

    assert [r.command for r in connection.requests] == [
        "threads",
        "stackTrace",
        "scopes",
        "variables",
        "evaluate",
    ]
    assert connection.requests[1].arguments == {"threadId": 7}
    assert connection.requests[2].arguments == {"frameId": 3}
    assert connection.requests[3].arguments == {"variablesReference": 11}
    assert connection.requests[4].arguments == {
        "expression": "a + 1",
        "context": "repl",
        "frameId": 2,
    }
