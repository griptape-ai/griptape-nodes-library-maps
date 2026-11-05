"""Street View failures reach the caller as NodeError, through the node's real requests call."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import google_street_view
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
    error = errors[0]
    assert isinstance(error, NodeError)
    assert "GOOGLE_MAPS_API_KEY is not set" in str(error)
    assert error.links is not None
    assert error.links[0].url == "#settings-secrets?filter=GOOGLE_MAPS_API_KEY"


def test_missing_key_stops_the_run(node: GoogleStreetView, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(node, "get_config_value", lambda **_kwargs: None)
    with pytest.raises(NodeError, match="GOOGLE_MAPS_API_KEY is not set"):
        _run(node)


def test_empty_address_is_a_validation_error(node: GoogleStreetView) -> None:
    node.set_parameter_value("address", "  ")
    errors = node.validate_before_node_run()
    assert errors is not None
    assert "Enter an address" in str(errors[0])


def test_bad_size_is_a_validation_error(node: GoogleStreetView) -> None:
    # The editor rejects values outside the dropdown, so a connected string is the way to reach this.
    node.parameter_values["size"] = "huge"
    errors = node.validate_before_node_run()
    assert errors is not None
    assert "'Size' must look like 'widthxheight'" in str(errors[0])


def test_valid_inputs_pass_validation(node: GoogleStreetView) -> None:
    assert node.validate_before_node_run() is None


def test_refused_key_links_to_settings(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    body = "The Google Maps Platform server rejected your request. The provided API key is invalid."
    send(lambda _request: _response(403, body))
    with pytest.raises(NodeError) as raised:
        _run(node)
    error = raised.value
    assert "Google refused the request" in str(error)
    assert error.fields == {"status_code": 403}
    assert error.response == {"text": body}
    assert error.links is not None
    assert error.links[0].url == "#settings-secrets?filter=GOOGLE_MAPS_API_KEY"
    assert node.parameter_output_values["status"] == str(error)


def test_no_imagery_names_the_address(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    send(lambda _request: _response(404))
    with pytest.raises(NodeError, match="No Street View imagery was found for '1600 Amphitheatre Parkway'") as raised:
        _run(node)
    assert raised.value.fields == {"status_code": 404}
    assert raised.value.response is None


def test_bad_request(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    send(lambda _request: _response(400, "Invalid request."))
    with pytest.raises(NodeError, match="Google rejected the request") as raised:
        _run(node)
    assert raised.value.response == {"text": "Invalid request."}


def test_rate_limit(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    send(lambda _request: _response(429))
    with pytest.raises(NodeError, match="rate-limiting"):
        _run(node)


def test_unexpected_status(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    send(lambda _request: _response(502, "Bad gateway"))
    with pytest.raises(NodeError, match=r"unexpected status \(502\)") as raised:
        _run(node)
    assert raised.value.fields == {"status_code": 502}


def test_connection_failure_does_not_leak_the_key(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    def refuse(request: requests.PreparedRequest) -> requests.Response:
        msg = f"connection refused for {request.url}"
        raise requests.ConnectionError(msg)

    send(refuse)
    with pytest.raises(NodeError, match="Could not reach the Street View API") as raised:
        _run(node)
    assert API_KEY not in str(raised.value)
    assert raised.value.fields == {"error_type": "ConnectionError"}


def test_timeout(node: GoogleStreetView, send: Callable[[Sender], None]) -> None:
    def time_out(_request: requests.PreparedRequest) -> requests.Response:
        raise requests.Timeout

    send(time_out)
    with pytest.raises(NodeError, match="did not respond within 30 seconds"):
        _run(node)


def test_success_saves_the_image(
    node: GoogleStreetView, send: Callable[[Sender], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    send(lambda _request: _response(200, "jpeg-bytes"))
    monkeypatch.setattr(node, "_handle_api_response", lambda response: f"saved:{response.status_code}")
    _run(node)
    assert node.parameter_output_values["street_view_image"].value == "saved:200"
    assert google_street_view.SERVICE == "Google_Maps"
