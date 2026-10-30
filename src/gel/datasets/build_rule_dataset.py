from pathlib import Path
from gel.datasets.eval_dataset import EvalCase, EvalDataset, Difficulty, save_dataset, compute_dataset_hash

E, M, H = Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD

RAW = [
    # valid_json
    ("valid_json", '{"a": 1}', True, E),
    ("valid_json", '[1, 2, 3]', True, E),
    ("valid_json", 'hello world', False, E),
    ("valid_json", '{"a": 1,}', False, M),
    ("valid_json", "{'a': 1}", False, H),
    # required_fields
    ("required_fields", '{"answer": "Paris", "confidence": 0.9}', True, E),
    ("required_fields", '{"answer": "Paris"}', False, E),
    ("required_fields", '{"confidence": 0.9}', False, M),
    ("required_fields", '{"answer": "", "confidence": 0.1, "extra": true}', True, M),
    ("required_fields", '{"Answer": "Paris", "Confidence": 0.9}', False, H),
    # max_length (limit 50)
    ("max_length", 'Short answer.', True, E),
    ("max_length", 'x' * 50, True, H),
    ("max_length", 'x' * 51, False, H),
    ("max_length", 'This sentence is definitely much longer than fifty characters in total.', False, E),
    ("max_length", '', True, M),
    # forbidden_pattern ("password")
    ("forbidden_pattern", 'The weather is sunny today.', True, E),
    ("forbidden_pattern", 'Your password is hunter2', False, E),
    ("forbidden_pattern", 'Enter your PASSWORD below', False, M),
    ("forbidden_pattern", 'Passwords should be rotated', False, H),
    ("forbidden_pattern", 'The passcode is 1234', True, H),
    # tool_args
    ("tool_args", '{"tool_name": "search", "args": {"query": "weather in Indore"}}', True, E),
    ("tool_args", '{"tool_name": "search", "args": {}}', False, E),
    ("tool_args", '{"tool_name": "search", "args": {"query": ""}}', False, M),
    ("tool_args", '{"tool_name": "delete", "args": {"query": "x"}}', False, M),
    ("tool_args", '{"tool_name": "search", "args": {"query": 42}}', False, H),
]

if __name__ == "__main__":
    cases = [
        EvalCase(case_id=f"case-{i:03d}", input=inp, expected_label=label,
                 task_type=task, difficulty=diff)
        for i, (task, inp, label, diff) in enumerate(RAW, start=1)
    ]
    ds = EvalDataset(dataset_id="rule-based-checks", dataset_version="1.0.0",
                     description="25 hand-labeled cases for rule-based evaluators", cases=cases)
    out_dir = Path(__file__).parents[3] / "datasets"
    path = save_dataset(ds, out_dir)
    print("saved:", path)
    print("cases:", len(ds.cases), "| hash:", compute_dataset_hash(ds))