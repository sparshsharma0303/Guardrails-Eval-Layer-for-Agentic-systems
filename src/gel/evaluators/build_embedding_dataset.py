from pathlib import Path
from gel.datasets.eval_dataset import EvalCase, EvalDataset, Difficulty, save_dataset, compute_dataset_hash

E, M, H = Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD

# (task_type, candidate, reference, same_meaning, difficulty)
RAW = [
    ("semantic_similarity", "A kitten is resting on a rug.", "The cat sat on the mat.", True, E),
    ("semantic_similarity", "The meeting has been moved to 3 PM.", "We rescheduled the meeting to three in the afternoon.", True, M),
    ("semantic_similarity", "Python is a popular programming language.", "Many developers use Python for programming.", True, E),
    ("semantic_similarity", "The server crashed because it ran out of memory.", "An out-of-memory error brought the server down.", True, M),
    ("semantic_similarity", "Paris is the capital of France.", "France's capital city is Paris.", True, E),
    ("semantic_similarity", "Please reset your password using the link.", "Use the link to reset your password.", True, E),
    ("semantic_similarity", "The film was excellent and I enjoyed it.", "I loved the movie; it was great.", True, E),
    ("semantic_similarity", "Water boils at 100 degrees Celsius.", "At sea level, water reaches its boiling point at 100°C.", True, M),
    ("semantic_similarity", "The API returned an error for the invalid request.", "The request was invalid so the API responded with an error.", True, M),
    ("semantic_similarity", "She walked her dog in the park this morning.", "This morning she took the dog for a walk in the park.", True, E),
    ("semantic_similarity", "Quarterly revenue grew by twelve percent.", "The cat sat on the mat.", False, E),
    ("semantic_similarity", "The meeting has been moved to 3 PM.", "Water boils at 100 degrees Celsius.", False, E),
    ("semantic_similarity", "Python is a popular programming language.", "She walked her dog in the park this morning.", False, E),
    ("semantic_similarity", "The server crashed because it ran out of memory.", "The film was excellent and I enjoyed it.", False, E),
    ("semantic_similarity", "Paris is the capital of France.", "The API returned an error for the invalid request.", False, E),
    ("semantic_similarity", "I enjoy hiking in the mountains.", "The stock market closed lower on Friday.", False, E),
    ("semantic_similarity", "The recipe needs two cups of flour.", "The satellite was launched into orbit yesterday.", False, E),
    ("semantic_similarity", "Tickets for the concert sold out quickly.", "Photosynthesis converts sunlight into chemical energy.", False, E),
    ("semantic_similarity", "The new phone has a great camera.", "The football match ended in a draw.", False, E),
    ("semantic_similarity", "He apologised for being late to the interview.", "The bridge was closed for repairs.", False, E),
    # known limitation: opposite meaning, similar wording. Reported, not gated.
    ("negation_limitation", "Paris is not the capital of France.", "Paris is the capital of France.", False, H),
    ("negation_limitation", "The server did not crash.", "The server crashed because it ran out of memory.", False, H),
]

if __name__ == "__main__":
    cases = [EvalCase(case_id=f"emb-{i:03d}", input=cand, expected_output=ref,
                      expected_label=label, task_type=task, difficulty=diff)
             for i, (task, cand, ref, label, diff) in enumerate(RAW, start=1)]
    ds = EvalDataset(dataset_id="embedding-similarity", dataset_version="1.0.0",
                     description="Hand-labeled same-meaning pairs for the embedding benchmark", cases=cases)
    path = save_dataset(ds, Path(__file__).parents[3] / "datasets")
    print("saved:", path, "| cases:", len(cases), "| hash:", compute_dataset_hash(ds))