"""Builds a `DatasetSchema` snapshot from a pandas DataFrame, used to
ground the LLM's code generation in the dataset's real shape.
"""
from __future__ import annotations

import pandas as pd

from .models import ColumnInfo, DatasetSchema

_MAX_SAMPLE_VALUES = 3
_PREVIEW_ROWS = 3


def build_schema(df: pd.DataFrame) -> DatasetSchema:
    columns = [
        ColumnInfo(
            name=col,
            dtype=str(df[col].dtype),
            sample_values=[_to_python(v) for v in df[col].dropna().unique()[:_MAX_SAMPLE_VALUES]],
        )
        for col in df.columns
    ]
    return DatasetSchema(
        row_count=len(df),
        columns=columns,
        preview_markdown=df.head(_PREVIEW_ROWS).to_string(index=False),
    )


def _to_python(value: object) -> object:
    """Converts numpy scalar types to plain Python types for clean prompt/JSON rendering."""
    if hasattr(value, "item"):
        return value.item()
    return value
