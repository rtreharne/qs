"""Calculate one-way ANOVA F statistics for the zebrafish data sets.

Run from the repository root with:
    python3 qs/data/02/calculate_anova.py

The script writes ``solutions.csv`` in the same directory.  Its ``xxx``
column is the three-digit suffix of each ``zebrafish_xxx.csv`` file.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path


DATA_DIRECTORY = Path(__file__).resolve().parent
INPUT_PATTERN = re.compile(r"zebrafish_(\d{3})\.csv$")
OUTPUT_FILE = DATA_DIRECTORY / "solutions.csv"


def anova_f_statistic(csv_file: Path) -> float:
    """Return the standard one-way ANOVA F statistic for one data file."""
    groups: dict[str, list[float]] = defaultdict(list)

    with csv_file.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"conc_pc", "length_micron"}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise ValueError(f"{csv_file.name} must contain {sorted(required_columns)}")

        for row in reader:
            # Blank lengths are excluded, matching Excel's omission of blank cells.
            if row["length_micron"].strip():
                groups[row["conc_pc"]].append(float(row["length_micron"]))

    if len(groups) < 2 or any(len(values) == 0 for values in groups.values()):
        raise ValueError(f"{csv_file.name} needs at least two non-empty groups")

    all_values = [value for values in groups.values() for value in values]
    total_observations = len(all_values)
    number_of_groups = len(groups)
    if total_observations <= number_of_groups:
        raise ValueError(f"{csv_file.name} has no within-group degrees of freedom")

    grand_mean = sum(all_values) / total_observations
    between_sum_of_squares = sum(
        len(values) * (sum(values) / len(values) - grand_mean) ** 2
        for values in groups.values()
    )
    within_sum_of_squares = sum(
        sum((value - sum(values) / len(values)) ** 2 for value in values)
        for values in groups.values()
    )

    mean_square_between = between_sum_of_squares / (number_of_groups - 1)
    mean_square_within = within_sum_of_squares / (total_observations - number_of_groups)
    if mean_square_within == 0:
        raise ValueError(f"{csv_file.name} has zero within-group variation")
    return mean_square_between / mean_square_within


def main() -> None:
    results: list[tuple[int, float]] = []

    for csv_file in DATA_DIRECTORY.glob("zebrafish_*.csv"):
        match = INPUT_PATTERN.fullmatch(csv_file.name)
        if match:
            results.append((int(match.group(1)), anova_f_statistic(csv_file)))

    results.sort()
    if not results:
        raise FileNotFoundError("No zebrafish_100.csv to zebrafish_999.csv files found")

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["xxx", "F-statistic"])
        writer.writerows((number, f"{f_statistic:.2f}") for number, f_statistic in results)

    print(f"Wrote {len(results)} results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
