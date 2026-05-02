"""Acme Corp Policy RAG — Evaluation script.

Runs the 25 evaluation questions through the RAG pipeline and computes:
- Groundedness % (LLM-as-judge)
- Citation Accuracy %
- Latency p50/p95
"""

import json
import re
import statistics
import time
from pathlib import Path

# Ensure project root is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag_chain import ask
from src.config import OPENROUTER_API_KEY, OPENROUTER_MODEL


def load_eval_questions() -> list[dict]:
    """Load evaluation questions from JSON."""
    eval_path = Path(__file__).parent / "eval_questions.json"
    with open(eval_path) as f:
        return json.load(f)


def check_citation_accuracy(answer: str, expected_source: str) -> bool:
    """Check if the expected source document is cited in the answer.

    Handles multiple citation formats produced by the LLM:
      - [pto-and-leave-policy]
      - [Source 2: pto-and-leave-policy]
      - Non-breaking hyphens (U+2011) used by some models
    """
    # Normalise non-breaking hyphens and similar unicode dashes to ASCII hyphen
    normalised = answer.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    # Extract everything inside square brackets
    bracketed = re.findall(r"\[([^\]]+)\]", normalised)
    for item in bracketed:
        # Strip "Source N: " prefix if present
        item_clean = re.sub(r"^Source\s+\d+:\s*", "", item, flags=re.IGNORECASE).strip()
        if item_clean == expected_source:
            return True
    return False


def check_groundedness_with_llm(question: str, answer: str, context_chunks: list[dict]) -> bool:
    """Use Groq LLM as judge to check if answer is grounded in context.

    Returns True if the answer is fully supported by the context.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    context_text = "\n\n".join([c["text"] for c in context_chunks])

    judge_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are an impartial judge evaluating whether an AI assistant's answer "
            "is fully supported by the provided context. You must respond with ONLY "
            "'GROUNDED' or 'NOT_GROUNDED'.\n\n"
            "Rules:\n"
            "- 'GROUNDED': Every factual claim in the answer is supported by the context.\n"
            "- 'NOT_GROUNDED': The answer contains information not present in or "
            "contradicted by the context.\n"
            "- If the answer correctly states it cannot find the information, that is GROUNDED.\n"
            "- Minor paraphrasing is acceptable as long as the meaning is preserved."
        )),
        ("human", (
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer: {answer}\n\n"
            "Is this answer fully grounded in the context? Reply ONLY with "
            "'GROUNDED' or 'NOT_GROUNDED'."
        )),
    ])

    llm = ChatOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        model=OPENROUTER_MODEL,
        temperature=0.0,
        max_tokens=10,
        default_headers={
            "HTTP-Referer": "https://github.com/chindris-mihai-alexandru/policy-rag-app",
            "X-Title": "Acme Corp Policy RAG",
        },
    )

    chain = judge_prompt | llm
    response = chain.invoke({
        "context": context_text,
        "question": question,
        "answer": answer,
    })

    return "GROUNDED" in response.content.upper() and "NOT_GROUNDED" not in response.content.upper()


def run_evaluation():
    """Run the full evaluation pipeline."""
    questions = load_eval_questions()
    results = []
    latencies = []

    print(f"Running evaluation on {len(questions)} questions...")
    print(f"Using model: {OPENROUTER_MODEL}")
    print("-" * 60)

    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] {q['question']}")

        # Time the RAG call
        start = time.time()
        try:
            result = ask(q["question"])
            latency_ms = round((time.time() - start) * 1000)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "id": q["id"],
                "question": q["question"],
                "domain": q["domain"],
                "error": str(e),
                "grounded": False,
                "citation_accurate": False,
                "latency_ms": 0,
            })
            continue

        latencies.append(latency_ms)
        answer = result["answer"]
        chunks = result.get("chunks", [])

        # Check citation accuracy
        citation_ok = check_citation_accuracy(answer, q["expected_source"])

        # Check groundedness (with rate limit awareness)
        try:
            # Small delay to respect Groq rate limits
            time.sleep(2)
            grounded = check_groundedness_with_llm(
                q["question"], answer, chunks
            )
        except Exception as e:
            print(f"  Groundedness check failed: {e}")
            grounded = None  # Unknown

        status = "✅" if (grounded and citation_ok) else "⚠️" if (grounded or citation_ok) else "❌"
        print(f"  {status} Grounded: {grounded} | Citation: {citation_ok} | Latency: {latency_ms}ms")
        print(f"  Answer preview: {answer[:120]}...")

        results.append({
            "id": q["id"],
            "question": q["question"],
            "domain": q["domain"],
            "expected_source": q["expected_source"],
            "answer": answer,
            "sources_returned": [s["source"] for s in chunks] if chunks else [],
            "grounded": grounded,
            "citation_accurate": citation_ok,
            "latency_ms": latency_ms,
        })

    # Compute aggregate metrics
    valid_results = [r for r in results if "error" not in r]
    grounded_count = sum(1 for r in valid_results if r["grounded"] is True)
    grounded_total = sum(1 for r in valid_results if r["grounded"] is not None)
    citation_count = sum(1 for r in valid_results if r["citation_accurate"])

    metrics = {
        "total_questions": len(questions),
        "successful_queries": len(valid_results),
        "groundedness_pct": round(grounded_count / grounded_total * 100, 1) if grounded_total > 0 else 0,
        "citation_accuracy_pct": round(citation_count / len(valid_results) * 100, 1) if valid_results else 0,
        "latency_p50_ms": round(statistics.median(latencies)) if latencies else 0,
        "latency_p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0),
        "latency_mean_ms": round(statistics.mean(latencies)) if latencies else 0,
    }

    # Per-domain breakdown
    domains = set(r["domain"] for r in valid_results)
    domain_metrics = {}
    for domain in sorted(domains):
        domain_results = [r for r in valid_results if r["domain"] == domain]
        d_grounded = sum(1 for r in domain_results if r["grounded"] is True)
        d_grounded_total = sum(1 for r in domain_results if r["grounded"] is not None)
        d_citation = sum(1 for r in domain_results if r["citation_accurate"])
        domain_metrics[domain] = {
            "count": len(domain_results),
            "groundedness_pct": round(d_grounded / d_grounded_total * 100, 1) if d_grounded_total > 0 else 0,
            "citation_accuracy_pct": round(d_citation / len(domain_results) * 100, 1) if domain_results else 0,
        }

    output = {
        "metrics": metrics,
        "domain_metrics": domain_metrics,
        "results": results,
    }

    # Save results
    output_path = Path(__file__).parent / "eval_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total questions: {metrics['total_questions']}")
    print(f"Successful queries: {metrics['successful_queries']}")
    print(f"Groundedness: {metrics['groundedness_pct']}%")
    print(f"Citation Accuracy: {metrics['citation_accuracy_pct']}%")
    print(f"Latency p50: {metrics['latency_p50_ms']}ms")
    print(f"Latency p95: {metrics['latency_p95_ms']}ms")
    print(f"Latency mean: {metrics['latency_mean_ms']}ms")
    print(f"\nPer-domain breakdown:")
    for domain, dm in domain_metrics.items():
        print(f"  {domain}: {dm['count']} questions | "
              f"Groundedness: {dm['groundedness_pct']}% | "
              f"Citation Accuracy: {dm['citation_accuracy_pct']}%")
    print(f"\nResults saved to: {output_path}")

    return output


if __name__ == "__main__":
    run_evaluation()
