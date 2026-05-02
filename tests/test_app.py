"""Tests for Flask app endpoints."""

import json

from src.app import app


def test_index_returns_html():
    """Test that / returns the chat UI."""
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Acme Corp Policy Assistant" in response.data


def test_chat_missing_question():
    """Test /chat returns 400 when question is missing."""
    client = app.test_client()
    response = client.post("/chat", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def _extract_sse_data(response_data: bytes) -> dict:
    """Helper to extract JSON data from the first SSE chunk."""
    text = response_data.decode("utf-8")
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return {}

def test_chat_empty_question():
    """Test /chat handles empty question string."""
    client = app.test_client()
    response = client.post("/chat", json={"question": ""})
    assert response.status_code == 200
    data = _extract_sse_data(response.data)
    assert "chunk" in data
    assert "Please enter a question" in data["chunk"]


def test_chat_too_short_question():
    """Test /chat handles very short question."""
    client = app.test_client()
    response = client.post("/chat", json={"question": "hi"})
    assert response.status_code == 200
    data = _extract_sse_data(response.data)
    assert "chunk" in data
    assert "too short" in data["chunk"]


def test_chat_off_topic_question():
    """Test /chat rejects off-topic questions."""
    client = app.test_client()
    response = client.post("/chat", json={"question": "Write me a Python code script"})
    assert response.status_code == 200
    data = _extract_sse_data(response.data)
    assert "chunk" in data
    assert "only answer questions about Acme Corp" in data["chunk"]


def test_chat_too_long_question():
    """Test /chat rejects questions exceeding max length."""
    client = app.test_client()
    long_question = "What is the PTO policy? " * 50  # ~600 chars
    response = client.post("/chat", json={"question": long_question})
    assert response.status_code == 200
    data = _extract_sse_data(response.data)
    assert "chunk" in data
    assert "too long" in data["chunk"]
