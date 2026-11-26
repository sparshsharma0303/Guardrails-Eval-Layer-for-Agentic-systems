from collections import Counter
from pathlib import Path
from gel.datasets.eval_dataset import load_dataset
from gel.groundedness.models import Claim
from gel.groundedness.evidence_retrieval import retrieve_evidence
from gel.groundedness.entailment import check_entailment
from gel.schema.trace import RetrievedDocument

THRESHOLD = 0.80
LABELS = ["entailed", "contradicted", "not_enough_info"]

if __name__ == "__main__":
    ds = load_dataset(Path(__file__).parents[2] / "datasets" / "claim-entailment__v1.0.0.json")

    results = []  # (case, predicted label, reason, number of evidence spans)
    for c in ds.cases:
        docs = [RetrievedDocument(doc_id="ctx", content=c.expected_output)]
        claim = Claim(text=c.input)
        evidence = retrieve_evidence(claim.text, docs, top_k=2)
        verdict = check_entailment(claim, evidence)
        results.append((c, verdict.label.value, verdict.reason, len(evidence)))

    correct = sum(pred == c.task_type for c, pred, _, _ in results)
    accuracy = correct / len(results)
    print(f"agreement with human labels: {correct}/{len(results)} = {accuracy:.1%}")

    for lab in LABELS:
        rows = [r for r in results if r[0].task_type == lab]
        print(f"  {lab}: {sum(r[1] == lab for r in rows)}/{len(rows)}")

    confusion = Counter((c.task_type, pred) for c, pred, _, _ in results)
    print("confusion (human -> pipeline):")
    for h in LABELS:
        print("  ", h, {p: confusion[(h, p)] for p in LABELS})

    for c, pred, reason, n_ev in results:
        if pred != c.task_type:
            print(f"MISS {c.case_id} [{c.difficulty.value}] human={c.task_type} "
                  f"pipeline={pred} evidence_spans={n_ev} | {c.input} | {reason}")

    assert accuracy >= THRESHOLD, f"agreement {accuracy:.1%} is below the {THRESHOLD:.0%} bar"
    print("groundedness benchmark passed")