import argparse

from .data import read_data
from .model import ShiftSchedulingModel, export_to_excel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input Excel path")
    parser.add_argument("--output", default="schedule_output.xlsx", help="Output Excel path")
    args = parser.parse_args()

    data = read_data(args.input)
    model = ShiftSchedulingModel(data)
    model.build()
    model.solve()
    schedule_df, hours_df, kpi_df = model.results()
    export_to_excel(schedule_df, hours_df, kpi_df, args.output)


if __name__ == "__main__":
    main()

