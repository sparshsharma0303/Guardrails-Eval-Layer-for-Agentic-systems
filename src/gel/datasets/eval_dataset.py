from enum import Enum
from pydantic import BaseModel,Field
from pydantic import ValidationError,field_validator
from datetime import datetime,timezone
from typing import List
import json
import hashlib
import time

def get_utc_datetime():
    return datetime.now(timezone.utc)



class Difficulty(str,Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class EvalCase(BaseModel):
    case_id: str
    input : str
    expected_output: str|None = None
    expected_label: bool 
    task_type: str 
    difficulty: Difficulty


class EvalDataset(BaseModel):
    dataset_id: str 
    dataset_version: str 
    created_at: datetime = Field(default_factory=get_utc_datetime)
    description :str| None = None 
    cases: list[EvalCase] = Field(default_factory=list)
    @field_validator("cases")
    @classmethod
    def check_unique_case_id(cls, v: List[EvalCase]) -> List[EvalCase]:
        ids = [c.case_id for c in v]
        if len(ids) != len(set(ids)):
            raise ValueError("case_id must be unique.")
        return v

def compute_dataset_hash(dataset:EvalDataset) ->str:
    cases_data = [case.model_dump(mode="json") for case in dataset.cases]
    combined = {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version, 
        "cases": cases_data
    }
    str_obj = json.dumps(combined,sort_keys=True)
    hash_object = hashlib.sha256(str_obj.encode())
    key = hash_object.hexdigest()
    return key



if __name__ == "__main__":
    # # case 1 test 1 
    # case1 = EvalCase(case_id = "dummy_case_id", input= "dummy_input", expected_label=True, task_type="dummy_task",difficulty=Difficulty.EASY)
    # case2 = EvalCase(case_id = "dummy_case_id2", input= "dummy_input2", expected_label=False, task_type="dummy_task2",difficulty=Difficulty.HARD)
    # case3 = EvalCase(case_id = "dummy_case_id2", input= "dummy_input3", expected_label=False, task_type="dummy_task3",difficulty=Difficulty.MEDIUM)
    # raw = case1.model_dump_json()
    # rebuilt = EvalCase.model_validate_json(raw)
    # assert case1 == rebuilt, "the round trip failed"
    # try:
    #     EvalCase(case_id = "dummy_case_id", input= "dummy_input", expected_label=True, task_type="dummy_task",difficulty="impossibe")
    #     assert False, "should have raised"

    # except ValidationError :
    #     print("validation error raise")
    # print("all cases passed")

    # ds1 = EvalDataset(dataset_id="id_1",dataset_version="1.0.0",cases=[case1,case2])
    # raw = ds1.model_dump_json()
    # rebuilt = EvalDataset.model_validate_json(raw)
    # assert rebuilt == ds1 and isinstance(rebuilt.cases[0],EvalCase),"round trip failed"
    # try:
    #     ds2 = EvalDataset(dataset_id="id_1",dataset_version="1.0.0",cases=[case2, case3])
    #     assert False, "should have raised"
    # except ValidationError:
    #     print("duplicate case id were found")
    # print("all test cases passed ")

    # test case description : Two datasets with the same cases but different created_at and description give the same hash.
    # --- hash tests ---
    case1 = EvalCase(case_id="dummy_case_id", input="dummy_input", expected_label=True,
                    task_type="dummy_task", difficulty=Difficulty.EASY)
    case2 = EvalCase(case_id="dummy_case_id2", input="dummy_input2", expected_label=False,
                    task_type="dummy_task2", difficulty=Difficulty.HARD)

    ds1 = EvalDataset(dataset_id="id_1", dataset_version="1.0.0", cases=[case1, case2],
                    description="abc",
                    created_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
    ds2 = EvalDataset(dataset_id="id_1", dataset_version="1.0.0", cases=[case1, case2],
                    description="xyz",
                    created_at=datetime(2025, 6, 1, tzinfo=timezone.utc))
    # 1. description / created_at don't affect the hash
    assert compute_dataset_hash(ds1) == compute_dataset_hash(ds2), "metadata changed the hash"

    # 2. changing one case's input changes the hash
    case1_changed = EvalCase(case_id="dummy_case_id", input="CHANGED", expected_label=True,
                            task_type="dummy_task", difficulty=Difficulty.EASY)
    ds3 = EvalDataset(dataset_id="id_1", dataset_version="1.0.0", cases=[case1_changed, case2])
    assert compute_dataset_hash(ds1) != compute_dataset_hash(ds3), "content change not detected"

    # 3. deterministic
    assert compute_dataset_hash(ds1) == compute_dataset_hash(ds1), "hash not deterministic"

    print("all hash tests passed")








