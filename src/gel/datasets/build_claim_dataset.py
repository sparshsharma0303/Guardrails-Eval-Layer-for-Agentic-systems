from pathlib import Path
from gel.datasets.eval_dataset import EvalCase, EvalDataset, Difficulty, save_dataset, compute_dataset_hash

E, M, H = Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD

CTX = {
    "eiffel": "The Eiffel Tower is located in Paris. It was completed in 1889 and stands about 330 metres tall.",
    "python": "Python was created by Guido van Rossum and first released in 1991. It emphasizes code readability.",
    "everest": "Mount Everest is the highest mountain above sea level. It is located in the Himalayas on the border between Nepal and China.",
    "water": "Water boils at 100 degrees Celsius at sea level. At higher altitudes, the boiling point is lower.",
    "revenue": "The company reported revenue of 12 million dollars in 2023, up from 10 million in 2022.",
    "curie": "Marie Curie won the Nobel Prize in Physics in 1903 and the Nobel Prize in Chemistry in 1911.",
    "library": "The library opens at 9 AM and closes at 5 PM on weekdays. It is closed on weekends.",
    "photo": "Photosynthesis converts light energy into chemical energy. Plants use carbon dioxide and water, and release oxygen.",
}

ENT, CON, NEI = "entailed", "contradicted", "not_enough_info"

# (context key, claim, human verdict, difficulty)
RAW = [
    ("eiffel", "The Eiffel Tower was completed in 1889.", ENT, E),
    ("eiffel", "The Eiffel Tower is about 330 metres tall.", ENT, E),
    ("python", "Python was first released in 1991.", ENT, E),
    ("python", "Guido van Rossum created Python.", ENT, E),
    ("everest", "Mount Everest lies on the Nepal-China border.", ENT, M),
    ("water", "Water boils at a lower temperature at high altitude.", ENT, M),
    ("revenue", "Revenue increased between 2022 and 2023.", ENT, M),
    ("curie", "Marie Curie won Nobel Prizes in two different fields.", ENT, H),
    ("library", "The library is closed on Saturdays.", ENT, M),
    ("photo", "Plants release oxygen during photosynthesis.", ENT, E),

    ("eiffel", "The Eiffel Tower was completed in 1925.", CON, E),
    ("eiffel", "The Eiffel Tower is located in London.", CON, E),
    ("python", "Python was first released in 2005.", CON, E),
    ("python", "Python was created by Dennis Ritchie.", CON, E),
    ("everest", "Mount Everest is located in the Andes.", CON, E),
    ("water", "Water boils at a higher temperature at high altitude.", CON, M),
    ("revenue", "Revenue decreased between 2022 and 2023.", CON, M),
    ("curie", "Marie Curie won the Nobel Prize in Physics in 1911.", CON, H),
    ("library", "The library is open on Sundays.", CON, M),
    ("photo", "Plants release carbon dioxide during photosynthesis.", CON, M),

    ("eiffel", "The Eiffel Tower was designed by Gustave Eiffel.", NEI, H),
    ("eiffel", "The Eiffel Tower receives millions of visitors each year.", NEI, M),
    ("python", "Python is the most popular programming language in the world.", NEI, M),
    ("python", "Python is slower than C.", NEI, H),
    ("everest", "Mount Everest is 8,849 metres tall.", NEI, H),
    ("water", "Water freezes at 0 degrees Celsius.", NEI, H),
    ("revenue", "The company was profitable in 2023.", NEI, M),
    ("curie", "Marie Curie was born in Poland.", NEI, H),
    ("library", "The library has a cafe.", NEI, E),
    ("photo", "Photosynthesis occurs in the chloroplasts.", NEI, H),
]

if __name__ == "__main__":
    cases = [EvalCase(case_id=f"claim-{i:03d}", input=claim, expected_output=CTX[key],
                    expected_label=(verdict == ENT), task_type=verdict, difficulty=diff)
            for i, (key, claim, verdict, diff) in enumerate(RAW, start=1)]
    ds = EvalDataset(dataset_id="claim-entailment", dataset_version="1.0.0",
                    description="30 hand-labeled (claim, context) cases: 10 entailed, 10 contradicted, 10 not_enough_info",
                    cases=cases)
    path = save_dataset(ds, Path(__file__).parents[3] / "datasets")
    print("saved:", path, "| cases:", len(cases), "| hash:", compute_dataset_hash(ds))