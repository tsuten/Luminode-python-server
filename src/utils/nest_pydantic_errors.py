from typing import Any
from pydantic import BaseModel

def nest_pydantic_errors(errors: list[dict[str, Any]]) -> dict[str, Any]:
    """Pydantic ValidationError(errors()) を階層構造に変換する。

    例:
        loc=["parent", "child", "field"], msg="field required"
    ->  {"parent": {"child": {"field": [{"msg": "field required", "type": "value_error.missing"}]}}}
    """
    tree: dict[str, Any] = {}
    for error in errors:
        loc = [str(p) for p in error.get("loc", [])]
        msg = error.get("msg")
        err_type = error.get("type")

        # 空の loc は __root__ に積む
        if not loc:
            loc = ["__root__"]

        cursor = tree
        for key in loc[:-1]:
            if key not in cursor or not isinstance(cursor.get(key), dict):
                cursor[key] = {}
            cursor = cursor[key]

        leaf_key = loc[-1]
        leaf = cursor.get(leaf_key)
        if leaf is None:
            cursor[leaf_key] = [{"msg": msg, "type": err_type}]
        elif isinstance(leaf, list):
            leaf.append({"msg": msg, "type": err_type})
        else:
            # 予期せぬ型衝突時は _errors 配下に集約
            cursor[leaf_key] = {
                "_errors": [{"msg": msg, "type": err_type}]
            }
    return tree
