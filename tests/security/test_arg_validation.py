from gel.security.arg_validation import validate_tool_args


def test_valid_args():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs", "limit": 10}
    assert validate_tool_args(args, schema) == []


def test_missing_arg():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs"}
    assert validate_tool_args(args, schema) == ["missing argument 'limit'"]


def test_extra_arg():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs", "limit": 10, "admin": True}
    assert validate_tool_args(args, schema) == ["unexpected argument 'admin'"]


def test_wrong_type():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs", "limit": "10"}
    assert validate_tool_args(args, schema) == [
        "argument 'limit' expected int, got str"
    ]


def test_multiple_problems_reported_in_predictable_order():
    schema = {"query": str, "limit": int, "offset": int}
    # 'query' is wrong type, 'limit' is missing, 'offset' is valid, 'debug' is extra
    args = {"query": 123, "offset": 0, "debug": True}

    assert validate_tool_args(args, schema) == [
        "argument 'query' expected str, got int",
        "missing argument 'limit'",
        "unexpected argument 'debug'",
    ]


def test_empty_args_and_empty_schema():
    assert validate_tool_args({}, {}) == []


def test_bool_is_rejected_when_int_expected():
    schema = {"limit": int}
    args = {"limit": True}
    assert validate_tool_args(args, schema) == [
        "argument 'limit' expected int, got bool"
    ]


def test_bool_is_accepted_when_bool_expected():
    schema = {"dry_run": bool}
    args = {"dry_run": True}
    assert validate_tool_args(args, schema) == []