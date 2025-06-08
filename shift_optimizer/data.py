from dataclasses import dataclass
import pandas as pd


@dataclass
class InputData:
    """Container for input tables loaded from Excel."""

    staff: pd.DataFrame
    availability: pd.DataFrame
    demand: pd.DataFrame
    wages: pd.Series


def read_data(path: str) -> InputData:
    """Load the required tables from ``path``."""
    xls = pd.ExcelFile(path)
    staff = pd.read_excel(xls, "Staff")
    avail = pd.read_excel(xls, "Availability")
    demand = pd.read_excel(xls, "Demand")
    wages = pd.read_excel(xls, "Wages").iloc[0]
    return InputData(staff, avail, demand, wages)

