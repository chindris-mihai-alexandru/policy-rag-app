"""Acme Corp Policy RAG — Flask web application.

Endpoints:
    GET  /       — Chat UI
    POST /chat   — API endpoint for questions
    GET  /health — Health check
    GET  /healthz — Health check (Render alias)
"""

import time

from flask import Flask, jsonify, render_template, request

from src.guardrails import validate_input, validate_output

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)

# Background startup: ingest corpus and warm up models in a thread so the
# port binds immediately and Render health checks pass. The first /chat
# request will block briefly if init isn't done yet.
import threading
from src.config import OPENROUTER_API_KEY

def _startup():
    from src.ingest import ingest_documents
    from src.rag_chain import warm_up
    # force=False → skips ingest if build-time already populated the DB
    result = ingest_documents(force=False)
    print(f"[startup] ingest: {result.get('status')} — {result.get('message')}")
    warm_up()
    print("[startup] warm-up complete")

if OPENROUTER_API_KEY:
    threading.Thread(target=_startup, daemon=True).start()


@app.route("/")
def index():
    """Serve the chat UI."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat API requests.

    Expects JSON: {"question": "..."}
    Returns JSON: {"answer": "...", "sources": [...], "latency_ms": ...}
    """
    data = request.get_json(silent=True)
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field in request body."}), 400

    question = data["question"].strip()

    # Validate input
    validation = validate_input(question)
    if not validation["valid"]:
        return jsonify({"answer": validation["error"], "sources": [], "latency_ms": 0}), 200

    # Time the RAG pipeline
    start = time.time()
    try:
        from src.rag_chain import ask
        result = ask(question)
    except Exception as e:
        return jsonify(
            {
                "answer": (
                    "I'm sorry, I encountered an error processing your question. "
                    "Please try again or contact HR at hr@acmecorp.com."
                ),
                "sources": [],
                "error": str(e),
                "latency_ms": round((time.time() - start) * 1000),
            }
        ), 200

    latency_ms = round((time.time() - start) * 1000)
    answer = validate_output(result["answer"])

    return jsonify(
        {
            "answer": answer,
            "sources": result["sources"],
            "latency_ms": latency_ms,
        }
    ), 200


@app.route("/health")
@app.route("/healthz")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "policy-rag-app"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
