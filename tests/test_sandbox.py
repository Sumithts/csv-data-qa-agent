"""Run with: python -m pytest tests/ -v"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest

from src.exceptions import SandboxExecutionError, UnsafeCodeError
from src.sandbox_executor import run_pandas_code, validate_code


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({
        "region": ["North", "South", "North", "West"],
        "revenue": [100, 200, 150, 300],
    })


def test_basic_aggregation(df: pd.DataFrame) -> None:
    assert run_pandas_code("result = df['revenue'].sum()", df) == 750


def test_groupby(df: pd.DataFrame) -> None:
    out = run_pandas_code("result = df.groupby('region')['revenue'].sum().to_dict()", df)
    assert out["North"] == 250


def test_rejects_import() -> None:
    with pytest.raises(UnsafeCodeError):
        validate_code("import os\nresult = 1")


def test_rejects_open() -> None:
    with pytest.raises(UnsafeCodeError):
        validate_code("result = open('/etc/passwd').read()")


def test_rejects_dunder() -> None:
    with pytest.raises(UnsafeCodeError):
        validate_code("result = ().__class__.__bases__")


def test_rejects_forbidden_module_reference() -> None:
    with pytest.raises(UnsafeCodeError):
        validate_code("result = os.system('ls')")


def test_missing_result_raises(df: pd.DataFrame) -> None:
    with pytest.raises(SandboxExecutionError):
        run_pandas_code("x = 1", df)


def test_runtime_error_wrapped(df: pd.DataFrame) -> None:
    with pytest.raises(SandboxExecutionError):
        run_pandas_code("result = df['does_not_exist'].sum()", df)


def test_cannot_mutate_source_df(df: pd.DataFrame) -> None:
    original = df.copy()
    run_pandas_code("df['revenue'] = 0\nresult = df['revenue'].sum()", df)
    assert df.equals(original), "sandbox must not mutate the caller's DataFrame"


def test_syntax_error_raises() -> None:
    with pytest.raises(UnsafeCodeError):
        validate_code("result = df[")
