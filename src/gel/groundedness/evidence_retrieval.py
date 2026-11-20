
import re
from gel.evaluators.embedding import embed_text, cosine_similarity
from gel.schema.trace import RetrievedDocument
from gel.groundedness.models import EvidenceSpan

def split_into_spans(text: str) -> list[str]:
    # limitation: abbreviations like "Dr. Smith" will split on the period.
    parts = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def retrieve_evidence(claim_text: str, documents: list[RetrievedDocument], top_k: int = 1, min_similarity: float = 0.3) -> list[EvidenceSpan]:
    claim_embedding = embed_text(claim_text)
    candidates: list[tuple[str, str, float]] = []

    for doc in documents:
        for span in split_into_spans(doc.content):
            span_embedding = embed_text(span)
            similarity = cosine_similarity(claim_embedding, span_embedding)
            candidates.append((doc.doc_id, span, similarity))

    qualified = [c for c in candidates if c[2] >= min_similarity]
    qualified.sort(key=lambda c: c[2], reverse=True)

    return [
        EvidenceSpan(doc_id=doc_id, text=span, similarity=similarity)
        for doc_id, span, similarity in qualified[:top_k]
    ]


if __name__ == "__main__":
    docs = [
        RetrievedDocument(doc_id="d1", content="Paris is the capital of France. It sits on the Seine river."),
        RetrievedDocument(doc_id="d2", content="The stock market closed lower on Friday. Oil prices rose."),
    ]
    claim = "France's capital city is Paris."

    r = retrieve_evidence(claim, docs)
    assert len(r) == 1 and r[0].doc_id == "d1" and "capital" in r[0].text

    r2 = retrieve_evidence(claim, docs, top_k=3, min_similarity=0.0)
    sims = [s.similarity for s in r2]
    assert len(r2) == 3 and sims == sorted(sims, reverse=True) and r2[0].doc_id == "d1"

    assert retrieve_evidence("Photosynthesis converts sunlight into chemical energy.", docs) == []
    assert retrieve_evidence(claim, []) == []
    print("retrieve_evidence tests passed")

