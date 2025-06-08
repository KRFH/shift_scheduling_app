"""Shift scheduling MILP model using ``PuLP``."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Tuple, List

import pandas as pd
import pulp

from .data import InputData

SLOT_HOURS = 4
W_COST = 1
W_WISH = 1
W_FAIR = 1


class BaseModel:
    """Simple wrapper around a ``PuLP`` model."""

    def __init__(self, name: str, sense: int = pulp.LpMinimize) -> None:
        self.problem = pulp.LpProblem(name, sense)

    def solve(self, *, msg: bool = True, time_limit: int = 300) -> None:
        self.problem.solve(pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit))
        status = pulp.LpStatus[self.problem.status]
        if status not in {
            "Optimal",
            "Not Solved",
            "Infeasible",
            "Unbounded",
            "Undefined",
        }:
            raise RuntimeError(f"Solver finished with status {status}")



@dataclass
class ShiftSchedulingModel(BaseModel):
    """MILP model for weekly shift scheduling."""

    data: InputData
    problem: pulp.LpProblem = field(init=False)
    x: Dict[Tuple[str, str, str], pulp.LpVariable] = field(init=False)
    h: Dict[str, pulp.LpVariable] = field(init=False)

    def __post_init__(self) -> None:
        super().__init__("ShiftScheduling")

    # internal caches used while building the model
    staff_ids: List[str] = field(init=False, repr=False)
    slot_keys: List[Tuple[str, str]] = field(init=False, repr=False)
    req: Dict[Tuple[str, str], int] = field(init=False, repr=False)
    avail_ok: Dict[Tuple[str, str, str], int] = field(init=False, repr=False)
    wish: Dict[Tuple[str, str, str], int] = field(init=False, repr=False)
    cost: Dict[Tuple[str, str, str], int] = field(init=False, repr=False)

    def build(self) -> None:
        """Construct all variables, constraints and the objective."""
        self._prepare_parameters()
        self._create_variables()
        self._add_constraints()
        self._set_objective()

    # ------------------------------------------------------------------
    # Model assembly helpers
    # ------------------------------------------------------------------
    def _prepare_parameters(self) -> None:
        staff_df = self.data.staff
        avail_df = self.data.availability
        demand_df = self.data.demand
        wages_row = self.data.wages

        self.staff_ids = list(staff_df["StaffID"])
        self.slot_keys = [(row.Date, row.Slot) for row in demand_df.itertuples()]

        self.req = demand_df.set_index(["Date", "Slot"]).RequiredCnt.to_dict()
        self.avail_ok = {
            (r.StaffID, r.Date, r.Slot): 1 if r.Availability in ("OK", "Wish") else 0
            for r in avail_df.itertuples()
        }
        self.wish = {
            (r.StaffID, r.Date, r.Slot): 1 if r.Availability == "Wish" else 0
            for r in avail_df.itertuples()
        }

        self.cost = {}
        for sid in self.staff_ids:
            base = int(staff_df.loc[staff_df.StaffID == sid, "HourlyWage"].values[0])
            for date, slot in self.slot_keys:
                is_night = slot == "22-26"
                dt = datetime.strptime(date, "%Y-%m-%d")
                is_holiday = dt.weekday() == 6
                mult = 1.0
                if is_night:
                    mult *= wages_row["NightRate"]
                if is_holiday:
                    mult *= wages_row["HolidayRate"]
                self.cost[(sid, date, slot)] = int(base * SLOT_HOURS * mult)

        self.dates_unique = avail_df["Date"].unique()

    def _create_variables(self) -> None:
        self.x = pulp.LpVariable.dicts(
            "x",
            ((sid, date, slot) for sid in self.staff_ids for (date, slot) in self.slot_keys),
            lowBound=0,
            upBound=1,
            cat="Binary",
        )
        self.h = pulp.LpVariable.dicts("h", self.staff_ids, lowBound=0, cat="Integer")
        self.mean_h = pulp.LpVariable("mean_h", lowBound=0)
        self.dev = pulp.LpVariable.dicts("dev", self.staff_ids, lowBound=0)
        self.y = pulp.LpVariable.dicts(
            "worked",
            ((sid, date) for sid in self.staff_ids for date in self.dates_unique),
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

    def _add_constraints(self) -> None:
        staff_df = self.data.staff

        for sid in self.staff_ids:
            age = int(staff_df.loc[staff_df.StaffID == sid, "Age"].values[0])
            for date, slot in self.slot_keys:
                if self.avail_ok.get((sid, date, slot), 0) == 0:
                    self.problem += self.x[(sid, date, slot)] == 0
                if age < 18 and slot == "22-26":
                    self.problem += self.x[(sid, date, slot)] == 0

        for date, slot in self.slot_keys:
            self.problem += (
                pulp.lpSum(self.x[(sid, date, slot)] for sid in self.staff_ids) >= self.req[(date, slot)]
            )

        for sid in self.staff_ids:
            self.problem += self.h[sid] == SLOT_HOURS * pulp.lpSum(
                self.x[(sid, date, slot)] for (date, slot) in self.slot_keys
            )
            min_h = int(staff_df.loc[staff_df.StaffID == sid, "WeeklyMinH"].values[0])
            max_h = int(staff_df.loc[staff_df.StaffID == sid, "WeeklyMaxH"].values[0])
            self.problem += self.h[sid] >= min_h
            self.problem += self.h[sid] <= max_h

        for sid in self.staff_ids:
            for date in self.dates_unique:
                slots_day = ["10-14", "14-18", "18-22", "22-26"]
                self.problem += pulp.lpSum(
                    self.x[(sid, date, slot)] for slot in slots_day if (date, slot) in self.slot_keys
                ) <= 2

        for sid in self.staff_ids:
            for date in self.dates_unique:
                slots_day = ["10-14", "14-18", "18-22", "22-26"]
                for slot in slots_day:
                    if (date, slot) in self.slot_keys:
                        self.problem += self.x[(sid, date, slot)] <= self.y[(sid, date)]
            self.problem += pulp.lpSum(self.y[(sid, date)] for date in self.dates_unique) <= 6

        self.problem += self.mean_h * len(self.staff_ids) == pulp.lpSum(self.h[sid] for sid in self.staff_ids)

        for sid in self.staff_ids:
            self.problem += self.dev[sid] >= self.h[sid] - self.mean_h
            self.problem += self.dev[sid] >= self.mean_h - self.h[sid]

    def _set_objective(self) -> None:
        total_cost = pulp.lpSum(
            self.cost[(sid, date, slot)] * self.x[(sid, date, slot)]
            for sid in self.staff_ids
            for (date, slot) in self.slot_keys
        )
        wish_sat = pulp.lpSum(
            self.wish.get((sid, date, slot), 0) * self.x[(sid, date, slot)]
            for sid in self.staff_ids
            for (date, slot) in self.slot_keys
        )
        fairness = pulp.lpSum(self.dev[sid] for sid in self.staff_ids)

        self.problem += W_COST * total_cost - W_WISH * wish_sat + W_FAIR * fairness

    def solve(self, *, msg: bool = True, time_limit: int = 300) -> None:
        if not hasattr(self, "x"):
            self.build()
        super().solve(msg=msg, time_limit=time_limit)

    def results(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        staff_df = self.data.staff
        demand_df = self.data.demand

        staff_ids = list(staff_df["StaffID"])
        slot_keys = [(row.Date, row.Slot) for row in demand_df.itertuples()]

        # Schedule sheet
        records = []
        for sid in staff_ids:
            for date, slot in slot_keys:
                if pulp.value(self.x[(sid, date, slot)]) > 0.5:
                    records.append({"StaffID": sid, "Date": date, "Slot": slot, "Assigned": 1})
        schedule_df = pd.DataFrame(records)

        # Hours sheet
        hours_df = pd.DataFrame({"StaffID": staff_ids, "Hours": [pulp.value(self.h[sid]) for sid in staff_ids]})

        # KPI sheet
        kpi_df = pd.DataFrame([{"ObjectiveValue": pulp.value(self.problem.objective)}])

        return schedule_df, hours_df, kpi_df


def export_to_excel(schedule_df: pd.DataFrame, hours_df: pd.DataFrame, kpi_df: pd.DataFrame, output_path: str) -> None:
    """Write results to an Excel file."""
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        schedule_df.to_excel(writer, sheet_name="Schedule", index=False)
        hours_df.to_excel(writer, sheet_name="Hours", index=False)
        kpi_df.to_excel(writer, sheet_name="KPI", index=False)

    print(f"Written solution to {output_path}")

