from pathlib import Path
from gel.datasets.eval_dataset import load_dataset
from gel.evaluators.embedding import embed_text, cosine_similarity

if __name__ == "__main__":
    ds = load_dataset(Path(__file__).parents[2] / "datasets" / "embedding-similarity__v1.0.0.json")

    def score(c):
        return cosine_similarity(embed_text(c.expected_output), embed_text(c.input))

    main = [c for c in ds.cases if c.task_type == "semantic_similarity"]
    same = [score(c) for c in main if c.expected_label]
    diff = [score(c) for c in main if not c.expected_label]

    mean_same, mean_diff = sum(same) / len(same), sum(diff) / len(diff)
    ranked_right = sum(s > d for s in same for d in diff)
    ranking_acc = ranked_right / (len(same) * len(diff))

    print(f"mean similar: {mean_same:.3f} | mean different: {mean_diff:.3f}")
    print(f"min similar: {min(same):.3f} | max different: {max(diff):.3f}")
    print(f"ranking accuracy: {ranking_acc:.2%}")
    for c in ds.cases:
        if c.task_type == "negation_limitation":
            print(f"known limitation {c.case_id}: {score(c):.3f} (human says different)")

    assert mean_same > mean_diff, "similar pairs don't score higher on average"
    assert ranking_acc >= 0.9, "embedding scores don't track human judgment"
    print("embedding benchmark passed")