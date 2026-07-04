# Allow direct execution from project root or with python -m
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pandas as pd

from src.utils.normalization import canonicalize


def search_dataframe(df, query, columns=None):
    """
    Flexible normalized search across a DataFrame.

    Example:
        search_dataframe(master_df, "speed paint")
        search_dataframe(master_df, "army painter", ["Company"])
    """

    if df is None or df.empty:
        return pd.DataFrame()

    search_value = canonicalize(query)

    if not search_value:
        return df.copy()

    if columns is None:
        columns = [
            "Paint_ID",
            "Company",
            "Brand",
            "Product_Line",
            "Paint_Name",
            "Paint_Type",
            "Status",
            "Source",
            "Notes",
        ]

    valid_columns = [
        column for column in columns
        if column in df.columns
    ]

    if not valid_columns:
        return pd.DataFrame(columns=df.columns)

    mask = pd.Series(False, index=df.index)

    for column in valid_columns:
        column_mask = (
            df[column]
            .fillna("")
            .astype(str)
            .apply(lambda cell: search_value in canonicalize(cell))
        )

        mask = mask | column_mask

    return df[mask].copy()


def search_by_column(df, column, query):
    if column not in df.columns:
        raise ValueError(f"Column not found: {column}")

    return search_dataframe(df, query, columns=[column])


def search_by_paint_name(df, query):
    return search_by_column(df, "Paint_Name", query)


def search_by_company(df, query):
    return search_by_column(df, "Company", query)


def search_by_brand(df, query):
    return search_by_column(df, "Brand", query)


def search_by_product_line(df, query):
    return search_by_column(df, "Product_Line", query)


def search_by_paint_type(df, query):
    return search_by_column(df, "Paint_Type", query)


def search_by_status(df, query):
    return search_by_column(df, "Status", query)
