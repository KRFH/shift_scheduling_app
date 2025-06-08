from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Tuple

import pandas as pd
import pulp

from .data import InputData

SLOT_HOURS = 4
W_COST = 1
W_WISH = 1
W_FAIR = 1


@dataclass
class ShiftSchedulingModel:
    """MILP model for weekly shift scheduling."""

    data: InputData
    problem: pulp.LpProblem = field(init=False)
    x: Dict[Tuple[str, str, str], pulp.LpVariable] = field(init=False)
    h: Dict[str, pulp.LpVariable] = field(init=False)

    def build(self) -> None:
        staff_df = self.data.staff
        avail_df = self.data.availability
        demand_df = self.data.demand
        wages_row = self.data.wages

        staff_ids = list(staff_df["StaffID"])
        slot_keys = [(row.Date, row.Slot) for row in demand_df.itertuples()]

        # Parameter dictionaries
        req = demand_df.set_index(["Date", "Slot"]).RequiredCnt.to_dict()
        avail_ok = {
            (r.StaffID, r.Date, r.Slot): 1 if r.Availability in ("OK", "Wish") else 0
            for r in avail_df.itertuples()
        }
        wish = {
            (r.StaffID, r.Date, r.Slot): 1 if r.Availability == "Wish" else 0
            for r in avail_df.itertuples()
        }

        cost = {}
        for sid in staff_ids:
            age = int(staff_df.loc[staff_df.StaffID == sid, "Age"].values[0])
            base = int(staff_df.loc[staff_df.StaffID == sid, "HourlyWage"].values[0])
            for date, slot in slot_keys:
                is_night = slot == "22-26"
                dt = datetime.strptime(date, "%Y-%m-%d")
                is_holiday = dt.weekday() == 6
                mult = 1.0
                if is_night:
                    mult *= wages_row["NightRate"]
                if is_holiday:
                    mult *= wages_row["HolidayRate"]
                cost[(sid, date, slot)] = int(base * SLOT_HOURS * mult)

        # Problem
        self.problem = pulp.LpProblem("ShiftScheduling", pulp.LpMinimize)

        # Decision variables x[sid,date,slot] ∈ {0,1}
        self.x = pulp.LpVariable.dicts(
            "x",
            ((sid, date, slot) for sid in staff_ids for (date, slot) in slot_keys),
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

        # Helper hours variables
        self.h = pulp.LpVariable.dicts("h", staff_ids, lowBound=0, cat="Integer")

        # Mean hours variable (continuous)
        mean_h = pulp.LpVariable("mean_h", lowBound=0)

        # Absolute deviation variables for fairness
        dev = pulp.LpVariable.dicts("dev", staff_ids, lowBound=0)

        # Availability & under‑18 night ban
        for sid in staff_ids:
            age = int(staff_df.loc[staff_df.StaffID == sid, "Age"].values[0])
            for date, slot in slot_keys:
                if avail_ok.get((sid, date, slot), 0) == 0:
                    self.problem += self.x[(sid, date, slot)] == 0
                if age < 18 and slot == "22-26":
                    self.problem += self.x[(sid, date, slot)] == 0

        # Demand fulfilment
        for date, slot in slot_keys:
            self.problem += (
                pulp.lpSum(self.x[(sid, date, slot)] for sid in staff_ids) >= req[(date, slot)]
            )

        # Weekly hours definition & bounds
        for sid in staff_ids:
            self.problem += self.h[sid] == SLOT_HOURS * pulp.lpSum(
                self.x[(sid, date, slot)] for (date, slot) in slot_keys
            )
            min_h = int(staff_df.loc[staff_df.StaffID == sid, "WeeklyMinH"].values[0])
            max_h = int(staff_df.loc[staff_df.StaffID == sid, "WeeklyMaxH"].values[0])
            self.problem += self.h[sid] >= min_h
            self.problem += self.h[sid] <= max_h

        # Daily max 8h (<=2 slots)
        dates_unique = avail_df["Date"].unique()
        for sid in staff_ids:
            for date in dates_unique:
                slots_day = ["10-14", "14-18", "18-22", "22-26"]
                self.problem += pulp.lpSum(
                    self.x[(sid, date, slot)] for slot in slots_day if (date, slot) in slot_keys
                ) <= 2

        # Weekly 1 day off
        y = pulp.LpVariable.dicts(
            "worked", ((sid, date) for sid in staff_ids for date in dates_unique), lowBound=0, upBound=1, cat="Binary"
        )
        for sid in staff_ids:
            for date in dates_unique:
                slots_day = ["10-14", "14-18", "18-22", "22-26"]
                for slot in slots_day:
                    if (date, slot) in slot_keys:
                        self.problem += self.x[(sid, date, slot)] <= y[(sid, date)]
            self.problem += pulp.lpSum(y[(sid, date)] for date in dates_unique) <= 6

        # Mean hours definition
        self.problem += mean_h * len(staff_ids) == pulp.lpSum(self.h[sid] for sid in staff_ids)

        # Absolute deviations
        for sid in staff_ids:
            self.problem += dev[sid] >= self.h[sid] - mean_h
            self.problem += dev[sid] >= mean_h - self.h[sid]

        # Objective
        total_cost = pulp.lpSum(
            cost[(sid, date, slot)] * self.x[(sid, date, slot)]
            for sid in staff_ids
            for (date, slot) in slot_keys
        )
        wish_sat = pulp.lpSum(
            wish.get((sid, date, slot), 0) * self.x[(sid, date, slot)]
            for sid in staff_ids
            for (date, slot) in slot_keys
        )
        fairness = pulp.lpSum(dev[sid] for sid in staff_ids)

        self.problem += W_COST * total_cost - W_WISH * wish_sat + W_FAIR * fairness

    def solve(self, *, msg: bool = True, time_limit: int = 300) -> None:
        if not hasattr(self, "problem"):
            self.build()
        self.problem.solve(pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit))
        if pulp.LpStatus[self.problem.status] not in (
            "Optimal",
            "Not Solved",
            "Infeasible",
            "Unbounded",
            "Undefined",
        ):
            raise RuntimeError("Solver finished with status " + pulp.LpStatus[self.problem.status])

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

