from starlette.requests import Request


def _receive_factory():
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return receive


def make_request(
    *,
    path: str = "/",
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_string: bytes = b"",
    path_params: dict | None = None,
) -> Request:
    raw_headers = []
    for key, value in (headers or {}).items():
        raw_headers.append((key.lower().encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query_string,
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
        "path_params": path_params or {},
    }
    return Request(scope, _receive_factory())


class FakeWideEvent:
    def __init__(self, *_args, **_kwargs):
        self.correlation_id = None
        self.added = []
        self.emitted = []

    def add_context(self, **kwargs):
        self.added.append(kwargs)

    def emit(self, *args):
        self.emitted.append(args)


class FakeSessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False
