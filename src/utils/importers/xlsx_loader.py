from pathlib import Path
import pandas as pd


def load_xlsx(file_path, sheet_name=0):
    """
    Loads an XLSX file into a pandas DataFrame.
    Requires openpyxl.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() != ".xlsx":
        raise ValueError(f"Not an XLSX file: {file_path}")

    return pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")


def list_xlsx_sheets(file_path):
    """
    Lists all sheet names in an XLSX workbook.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    excel_file = pd.ExcelFile(file_path, engine="openpyxl")
    return excel_file.sheet_names