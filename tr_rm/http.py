from httpx import HTTPTransport, Client, HTTPStatusError
# made available as a proxy
from httpx import HTTPStatusError  # noqa

context = {}


def client():
    if not context.get("client"):
        transport = HTTPTransport(retries=5)
        context["client"] = Client(transport=transport)
    return context["client"]
