"""Street View failures reach the caller as NodeError, through the node's real requests call."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import requests
from google_street_view import GoogleStreetView
from griptape_nodes.exe_types.core_types import NodeError
from requests.adapters import HTTPAdapter

API_KEY = "test-key-1234567890"
ADDRESS = "1600 Amphitheatre Parkway"

Sender = Callable[[requests.PreparedRequest], requests.Response]


def _response(status: int, text: str = "") -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response._content = text.encode()
    return response


@pytest.fixture
def send(monkeypatch: pytest.MonkeyPatch) -> Callable[[Sender], None]:
    """Route the node's real `requests.get` through a handler at the adapter level."""

    def install(handler: Sender) -> None:
        def fake_send(_self: HTTPAdapter, request: requests.PreparedRequest, **_kwargs: Any) -> requests.Response:
            return handler(request)

        monkeypatch.setattr(HTTPAdapter, "send", fake_send)

    return install


@pytest.fixture
def node(monkeypatch: pytest.MonkeyPatch) -> GoogleStreetView:
    street_view = object.__new__(GoogleStreetView)
    GoogleStreetView.__init__(street_view, name="street_view")
    street_view.set_parameter_value("address", ADDRESS)
    monkeypatch.setattr(street_view, "get_config_value", lambda **_kwargs: API_KEY)
    return street_view


def _run(node: GoogleStreetView) -> None:
    (task,) = node.process()
    task()


def test_missing_key_is_the_only_validation_error(node: GoogleStreetView, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(node, "get_config_value", lambda **_kwargs: None)
    node.set_parameter_value("address", "")
    errors = node.validate_before_node_run()
    assert errors is not None
    assert len(errors) == 1
    assert "GOOGLE_MAPS_API_KEY is not set" in str(errors[0])


def test_missing_key_stops_the_run(node: GoogleStreetView, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(node, "get_config_value", lambda **_kwargs: None)
    with pytest.raises(NodeError, match="GOOGLE_MAPS_API_KEY is not set"):
        _run(node)


def test_empty_address_is_a_validation_error(node: GoogleStreetView) -> None:
    node.set_parameter_value("address", "  ")
    errors = node.validate_before_node_run()
    assert errors is not None
    assert "Enter an address" in str(errors[0])


def test_refused_key_keeps_google_text_in_response(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    body = "The provided API key is invalid."
    send(lambda _request: _response(403, body))
    with pytest.raises(NodeError, match="Google Maps refused the API key") as raised:
        _run(node)
    assert raised.value.response == {"body": body}
    assert node.parameter_output_values["status"] == str(raised.value)


def test_no_imagery_names_the_address(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    send(lambda _request: _response(404))
    with pytest.raises(NodeError, match="No Street View imagery was found for '1600 Amphitheatre Parkway'"):
        _run(node)


def test_connection_failure_does_not_leak_the_key(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    def refuse(request: requests.PreparedRequest) -> requests.Response:
        msg = f"connection refused for {request.url}"
        raise requests.ConnectionError(msg)

    send(refuse)
    with pytest.raises(NodeError, match="Could not reach Google Maps") as raised:
        _run(node)
    assert API_KEY not in str(raised.value)


def test_other_request_failure_does_not_leak_the_key(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    def fail(request: requests.PreparedRequest) -> requests.Response:
        raise requests.TooManyRedirects(request.url)

    send(fail)
    with pytest.raises(NodeError, match="request to Google Maps failed") as raised:
        _run(node)
    assert API_KEY not in str(raised.value)


def test_loads_as_the_engine_does(monkeypatch: pytest.MonkeyPatch) -> None:
    path = Path(__file__).parents[3] / "google-maps" / "google_street_view.py"
    monkeypatch.syspath_prepend(str(path.parent))
    monkeypatch.setitem(sys.modules, "google-maps", None)
    spec = importlib.util.spec_from_file_location("engine_style_google_street_view", path)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(importlib.util.module_from_spec(spec))
