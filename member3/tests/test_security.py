"""
Security regression tests for the SPA fallback and API surface.

The fallback must never read a file outside ``member3/frontend/dist``, and
unmatched ``/api/*`` paths must answer JSON 404 — never SPA HTML.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from member3.backend.main import FRONTEND_DIST, app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _attack_paths() -> list[str]:
    """Encoded traversal forms. Plain ``/../`` segments are normalized away by
    HTTP clients (httpx, browsers) before the server sees them, so the real
    exploit surface — and what these tests pin — is the encoded variant."""
    return [
        "/..%2F..%2F.git%2Fconfig",
        "/%2e%2e/%2e%2e/.git/config",
        "/..%252F..%252F.git%252Fconfig",
        "/..%2F..%2Frequirements.txt",
        "/..%2F..%2Fdata%2Fexpected_delivery_format.csv",
        "/..%2F..%2Fbackend%2Fmain.py",
        "/..%2F..%2FREADME.md",
        "/assets/..%2F..%2F..%2F.git%2Fconfig",
        "/%2e%2e%2f%2e%2e%2f.git%2fconfig",
        "/..%2F..%2Fmember3%2FREADME.md",
    ]


@pytest.mark.parametrize("path", _attack_paths(), ids=lambda p: p.replace("/", "_").replace("%", "pct"))
def test_path_traversal_never_leaks_files(client, path):
    response = client.get(path)
    assert response.status_code == 404, f"{path} must be rejected with 404"
    body = response.content.decode("utf-8", errors="replace")
    assert "remote" not in body.lower() and "repositoryformatversion" not in body.lower()
    assert "fastapi" not in body.lower()
    assert response.headers.get("content-type", "").startswith("application/json")


def test_plain_dotdot_paths_never_leak(client):
    # Clients normalize plain ".." away, so the server can only ever see the
    # resolved path; assert no content can leak through it either way.
    response = client.get("/../.git/config")
    body = response.content.decode("utf-8", errors="replace").lower()
    assert "repositoryformatversion" not in body
    assert "[core]" not in body


def test_encoded_double_encoding_is_also_rejected(client):
    # Double-encoded traversal survives one decode pass as a literal filename
    # inside dist ("..%2F..%2F.git%2Fconfig"), which cannot exist. The server
    # must never interpret it as a path escape: assert no leak, not a 200.
    response = client.get("/..%252F..%252F.git%252Fconfig")
    body = response.content.decode("utf-8", errors="replace")
    assert response.status_code in (200, 404)
    assert "repositoryformatversion" not in body
    assert "[core]" not in body


def test_traversal_with_encoded_dots(client):
    response = client.get("/%2e%2e/%2e%2e/.git/config")
    assert response.status_code == 404


def test_unknown_api_paths_never_return_html(client):
    for path in ("/api/does-not-exist", "/api/foo/bar", "/api/jobs/x/export.pdf"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.headers.get("content-type", "").startswith("application/json")
        body = response.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert "<html" not in response.content.decode("utf-8", errors="replace").lower()


def test_known_files_inside_dist_still_served(client):
    if not FRONTEND_DIST.is_dir():
        pytest.skip("frontend dist not built")
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/html")
    asset_dir = FRONTEND_DIST / "assets"
    if asset_dir.is_dir():
        asset = next(asset_dir.iterdir())
        response = client.get(f"/assets/{asset.name}")
        assert response.status_code == 200


def test_error_pages_reveal_no_traceback_or_paths(client):
    response = client.get("/api/does-not-exist")
    body = response.content.decode("utf-8", errors="replace")
    for leak in ("Traceback", "/Users/", "FileNotFoundError", "frontend/dist"):
        assert leak not in body