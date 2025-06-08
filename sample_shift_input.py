import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ---------------------------
# 1. Staff sheet (30 members)
# ---------------------------
num_staff = 30
staff_ids = [f"S{str(i+1).zfill(2)}" for i in range(num_staff)]
names = [f"Staff_{str(i+1).zfill(2)}" for i in range(num_staff)]

np.random.seed(42)
ages = np.random.choice(range(17, 31), size=num_staff, replace=True)  # ages 17-30
hourly_wage = [1050 if age < 18 else np.random.randint(1100, 1301) for age in ages]
weekly_min_h = np.random.choice([4, 8, 12], size=num_staff)  # contract min
weekly_max_h = np.random.choice([20, 24, 28, 32], size=num_staff)  # contract max

staff_df = pd.DataFrame(
    {
        "StaffID": staff_ids,
        "Name": names,
        "Age": ages,
        "HourlyWage": hourly_wage,
        "WeeklyMinH": weekly_min_h,
        "WeeklyMaxH": weekly_max_h,
    }
)

# --------------------------------
# 2. Availability sheet
# --------------------------------
slots = ["10-14", "14-18", "18-22", "22-26"]
start_date = datetime(2025, 5, 26)  # Monday
dates = [start_date + timedelta(days=i) for i in range(7)]  # 7 days

availability_records = []
rng = np.random.default_rng(123)

for staff in staff_ids:
    for date in dates:
        for slot in slots:
            # Weighted random choice: 0.7 OK, 0.2 NG, 0.1 Wish
            availability = rng.choice(["OK", "NG", "Wish"], p=[0.7, 0.2, 0.1])
            availability_records.append(
                {"StaffID": staff, "Date": date.strftime("%Y-%m-%d"), "Slot": slot, "Availability": availability}
            )

availability_df = pd.DataFrame(availability_records)

# --------------------------------
# 3. Demand sheet
# --------------------------------
demand_records = []
for date in dates:
    weekday = date.weekday()  # 0=Mon,...,6=Sun
    for slot in slots:
        if weekday in [4, 5]:  # Fri, Sat
            req = {"10-14": 4, "14-18": 3, "18-22": 5, "22-26": 3}[slot]
        elif weekday == 6:  # Sun
            req = {"10-14": 3, "14-18": 3, "18-22": 4, "22-26": 2}[slot]
        else:  # Mon-Thu
            req = {"10-14": 3, "14-18": 2, "18-22": 4, "22-26": 2}[slot]
        demand_records.append({"Date": date.strftime("%Y-%m-%d"), "Slot": slot, "RequiredCnt": req})

demand_df = pd.DataFrame(demand_records)

# --------------------------------
# 4. Wages sheet
# --------------------------------
wages_df = pd.DataFrame({"NormalRate": [1.0], "NightRate": [1.25], "HolidayRate": [1.35]})

# --------------------------------
# 5. Write to Excel
# --------------------------------
file_path = "sample_shift_input.xlsx"
with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
    staff_df.to_excel(writer, sheet_name="Staff", index=False)
    availability_df.to_excel(writer, sheet_name="Availability", index=False)
    demand_df.to_excel(writer, sheet_name="Demand", index=False)
    wages_df.to_excel(writer, sheet_name="Wages", index=False)
