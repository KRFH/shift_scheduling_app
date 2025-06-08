#!/usr/bin/env python3
"""shift_optimizer_pulp.py

Shift scheduling optimisation using PuLP (MILP).
Reads Excel with sheets Staff, Availability, Demand, Wages.
Writes Schedule, Hours, KPI sheets.
Usage:
    python shift_optimizer_pulp.py --input sample_shift_input.xlsx --output schedule_output.xlsx
"""

import argparse
from datetime import datetime
import pandas as pd
import pulp


SLOT_HOURS = 4
W_COST = 1
W_WISH = 1
W_FAIR = 1


def read_data(path):
    xls = pd.ExcelFile(path)
    staff = pd.read_excel(xls, "Staff")
    avail = pd.read_excel(xls, "Availability")
    demand = pd.read_excel(xls, "Demand")
    wages = pd.read_excel(xls, "Wages").iloc[0]
    return staff, avail, demand, wages


def build_problem(staff_df, avail_df, demand_df, wages_row):
    staff_ids = list(staff_df["StaffID"])
    slot_keys = [(row.Date, row.Slot) for row in demand_df.itertuples()]

    # Parameter dictionaries
    req = demand_df.set_index(["Date", "Slot"]).RequiredCnt.to_dict()
    avail_ok = {
        (r.StaffID, r.Date, r.Slot): 1 if r.Availability in ("OK", "Wish") else 0 for r in avail_df.itertuples()
    }
    wish = {(r.StaffID, r.Date, r.Slot): 1 if r.Availability == "Wish" else 0 for r in avail_df.itertuples()}

    cost = {}
    for sid in staff_ids:
        age = int(staff_df.loc[staff_df.StaffID == sid, "Age"].values[0])
        base = int(staff_df.loc[staff_df.StaffID == sid, "HourlyWage"].values[0])
        for date, slot in slot_keys:
            is_night = 1 if slot == "22-26" else 0
            dt = datetime.strptime(date, "%Y-%m-%d")
            is_holiday = 1 if dt.weekday() == 6 else 0
            mult = 1.0
            if is_night:
                mult *= wages_row["NightRate"]
            if is_holiday:
                mult *= wages_row["HolidayRate"]
            cost[(sid, date, slot)] = int(base * SLOT_HOURS * mult)

    # Problem
    prob = pulp.LpProblem("ShiftScheduling", pulp.LpMinimize)

    # Decision variables x[sid,date,slot] ∈ {0,1}
    x = pulp.LpVariable.dicts(
        "x", ((sid, date, slot) for sid in staff_ids for (date, slot) in slot_keys), lowBound=0, upBound=1, cat="Binary"
    )

    # Helper hours variables
    h = pulp.LpVariable.dicts("h", staff_ids, lowBound=0, cat="Integer")

    # Mean hours variable (continuous)
    mean_h = pulp.LpVariable("mean_h", lowBound=0)

    # Absolute deviation variables for fairness
    dev = pulp.LpVariable.dicts("dev", staff_ids, lowBound=0)

    # Availability & under‑18 night ban
    for sid in staff_ids:
        age = int(staff_df.loc[staff_df.StaffID == sid, "Age"].values[0])
        for date, slot in slot_keys:
            if avail_ok.get((sid, date, slot), 0) == 0:
                prob += x[(sid, date, slot)] == 0
            if age < 18 and slot == "22-26":
                prob += x[(sid, date, slot)] == 0

    # Demand fulfilment
    for date, slot in slot_keys:
        prob += pulp.lpSum(x[(sid, date, slot)] for sid in staff_ids) >= req[(date, slot)]

    # Weekly hours definition & bounds
    for sid in staff_ids:
        prob += h[sid] == SLOT_HOURS * pulp.lpSum(x[(sid, date, slot)] for (date, slot) in slot_keys)
        min_h = int(staff_df.loc[staff_df.StaffID == sid, "WeeklyMinH"].values[0])
        max_h = int(staff_df.loc[staff_df.StaffID == sid, "WeeklyMaxH"].values[0])
        prob += h[sid] >= min_h
        prob += h[sid] <= max_h

    # Daily max 8h (<=2 slots)
    dates_unique = avail_df["Date"].unique()
    for sid in staff_ids:
        for date in dates_unique:
            slots_day = ["10-14", "14-18", "18-22", "22-26"]
            prob += pulp.lpSum(x[(sid, date, slot)] for slot in slots_day if (date, slot) in slot_keys) <= 2

    # Weekly 1 day off
    # introduce y_sd
    y = pulp.LpVariable.dicts(
        "worked", ((sid, date) for sid in staff_ids for date in dates_unique), lowBound=0, upBound=1, cat="Binary"
    )
    for sid in staff_ids:
        for date in dates_unique:
            slots_day = ["10-14", "14-18", "18-22", "22-26"]
            # If any slot assigned => y_sd =1
            for slot in slots_day:
                if (date, slot) in slot_keys:
                    prob += x[(sid, date, slot)] <= y[(sid, date)]
        prob += pulp.lpSum(y[(sid, date)] for date in dates_unique) <= 6

    # Mean hours definition
    prob += mean_h * len(staff_ids) == pulp.lpSum(h[sid] for sid in staff_ids)

    # Absolute deviations
    for sid in staff_ids:
        prob += dev[sid] >= h[sid] - mean_h
        prob += dev[sid] >= mean_h - h[sid]

    # Objective
    total_cost = pulp.lpSum(
        cost[(sid, date, slot)] * x[(sid, date, slot)] for sid in staff_ids for (date, slot) in slot_keys
    )
    wish_sat = pulp.lpSum(
        wish.get((sid, date, slot), 0) * x[(sid, date, slot)] for sid in staff_ids for (date, slot) in slot_keys
    )
    fairness = pulp.lpSum(dev[sid] for sid in staff_ids)

    prob += W_COST * total_cost - W_WISH * wish_sat + W_FAIR * fairness

    return prob, x, h


def solve_and_export(prob, x_vars, h_vars, staff_df, demand_df, output_path):
    prob.solve(pulp.PULP_CBC_CMD(msg=True, timeLimit=300))

    if pulp.LpStatus[prob.status] not in ("Optimal", "Not Solved", "Infeasible", "Unbounded", "Undefined"):
        raise RuntimeError("Solver finished with status " + pulp.LpStatus[prob.status])

    staff_ids = list(staff_df["StaffID"])
    slot_keys = [(row.Date, row.Slot) for row in demand_df.itertuples()]

    # Schedule sheet
    records = []
    for sid in staff_ids:
        for date, slot in slot_keys:
            if pulp.value(x_vars[(sid, date, slot)]) > 0.5:
                records.append({"StaffID": sid, "Date": date, "Slot": slot, "Assigned": 1})
    schedule_df = pd.DataFrame(records)

    # Hours sheet
    hours_df = pd.DataFrame({"StaffID": staff_ids, "Hours": [pulp.value(h_vars[sid]) for sid in staff_ids]})

    # KPI sheet
    kpi_df = pd.DataFrame([{"ObjectiveValue": pulp.value(prob.objective)}])

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        schedule_df.to_excel(writer, sheet_name="Schedule", index=False)
        hours_df.to_excel(writer, sheet_name="Hours", index=False)
        kpi_df.to_excel(writer, sheet_name="KPI", index=False)

    print(f"Written solution to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input Excel path")
    parser.add_argument("--output", default="schedule_output.xlsx", help="Output Excel path")
    args = parser.parse_args()

    staff, avail, demand, wages = read_data(args.input)
    prob, x_vars, h_vars = build_problem(staff, avail, demand, wages)
    solve_and_export(prob, x_vars, h_vars, staff, demand, args.output)


if __name__ == "__main__":
    main()
