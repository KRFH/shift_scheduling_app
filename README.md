# Shift Scheduling App

This repository contains a simple shift scheduling optimizer built with
[PuLP](https://github.com/coin-or/pulp).  The project is organised as a small
package with a command line interface exposed via the ``shift-optimizer``
script.

## Using Poetry

1. Install [Poetry](https://python-poetry.org/) if you do not have it.
2. Run `poetry install` to create the virtual environment.
3. Execute the optimizer with:

```bash
poetry run shift-optimizer --input sample_shift_input.xlsx --output schedule_output.xlsx
```

Sample input and output Excel files are provided.

## Dash Application

Run the interactive Dash app to upload an Excel file and see the results:

```bash
poetry run python dash_app/app.py
```
