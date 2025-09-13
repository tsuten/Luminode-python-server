from typing import Any


def format_exception_for_response(exc: Exception, *, pydantic_nester=None) -> Any:
    """例外を API/Socket 応答用の error ペイロードに変換する。

    - Pydantic ValidationError らしきものは `errors()` を階層化
    - それ以外は文字列化
    - ネスト関数は DI 可能（デフォルトは None のまま）
    """
    # Pydantic ValidationError 互換インターフェースを持つか
    if hasattr(exc, "errors") and callable(getattr(exc, "errors")) and pydantic_nester is not None:
        try:
            return pydantic_nester(exc.errors())  # type: ignore[arg-type]
        except Exception:
            # フォールバック: json() があれば使い、なければ文字列
            try:
                return getattr(exc, "json")()
            except Exception:
                return str(exc)

    return str(exc)


