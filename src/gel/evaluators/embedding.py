# src/gel/evaluators/embedding.py
import math
from collections.abc import Sequence
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: got {len(a)} and {len(b)}")

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)

def embed_text(text: str) -> list[float]:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model.encode(text).tolist()


if __name__ == "__main__":
    # 1. Identical vectors -> ~1.0
    sim_identical = cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert math.isclose(sim_identical, 1.0), f"Expected ~1.0, got {sim_identical}"
    print(f"Identical vectors:  {sim_identical}")

    # 2. Orthogonal vectors -> 0.0
    sim_orthogonal = cosine_similarity([1.0, 0.0], [0.0, 1.0])
    assert math.isclose(sim_orthogonal, 0.0), f"Expected 0.0, got {sim_orthogonal}"
    print(f"Orthogonal vectors: {sim_orthogonal}")

    # 3. Opposite vectors -> ~-1.0
    sim_opposite = cosine_similarity([1.0, 2.0, 3.0], [-1.0, -2.0, -3.0])
    assert math.isclose(sim_opposite, -1.0), f"Expected -1.0, got {sim_opposite}"
    print(f"Opposite vectors:   {sim_opposite}")

    # 4. Zero vector -> 0.0
    sim_zero = cosine_similarity([0.0, 0.0, 0.0], [1.0, 2.0, 3.0])
    assert sim_zero == 0.0, f"Expected 0.0, got {sim_zero}"
    print(f"Zero vector:        {sim_zero}")

    print("All cosine_similarity tests passed!")

    a = embed_text("The cat sat on the mat.")
    b = embed_text("A kitten is resting on a rug.")
    c = embed_text("Quarterly revenue grew by twelve percent.")
    sim_similar = cosine_similarity(a, b)
    sim_different = cosine_similarity(a, c)
    print(f"similar: {sim_similar:.3f}  different: {sim_different:.3f}")
    assert len(a) == 384, "unexpected embedding size"
    assert sim_similar > sim_different, "embeddings don't rank similar text higher"
    print("embed_text tests passed")