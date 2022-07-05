import argparse
import calendar
from datetime import date, timedelta
from typing import Dict

import pandas as pd
from rich import print
from rich.console import Console
from rich.table import Table
from workalendar.europe import Netherlands

from x3cli.x3 import X3

console = Console()


cal = Netherlands()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    today = date.today()
    parser.add_argument("-y", "--year", type=int, default=today.year)
    parser.add_argument("-m", "--month", type=int, default=today.month)

    args = parser.parse_args()
    return args


def date_range(start, end):
    result = []
    while start <= end:
        result.append(start)
        start += timedelta(days=1)
    return result


def last_day_of_month(year: int, month: int) -> date:
    first_day_of_month = date(year, month, 1)
    days_in_month = days_in_month = calendar.monthrange(year, month)[1]
    return first_day_of_month + timedelta(days=days_in_month - 1)


def month_date_range(year: int, month: int):
    first_day = date(year, month, 1)
    last_day = last_day_of_month(year=year, month=month)
    return date_range(first_day, last_day)


def add_missing_working_days(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    working_dates_in_month = [
        d for d in month_date_range(year, month) if cal.is_working_day(d)
    ]
    missing_days = set(working_dates_in_month) - set(df["date"])

    for i, d in enumerate(missing_days):
        df.loc[len(df) + i, "date"] = d

    return df.sort_values("date")


def create_df(lines: Dict, geldig: Dict, *, year: int, month: int):
    projects_df = pd.DataFrame.from_dict(geldig["projects"]).drop("wsts", axis=1)
    hours_df = pd.DataFrame.from_dict(lines)
    if hours_df.empty:  # If no hours were written yet, an empty DataFrame is created. We need the columns to exist.
        hours_df = pd.DataFrame(columns=["_id", "day", "month", "year", "employee", "project", "wst", "desc", "time", "created", "approved"], dtype=str)
    df = hours_df.merge(
        projects_df, left_on="project", right_on="code", how="left"
    )  # Left merge so holidays remain

    df.loc[df["project"] == "VBZ", "name"] = "Holiday"
    df = df.drop("project", axis=1)
    df = df.rename(columns={"name": "project"})

    df["date"] = pd.to_datetime(df[["year", "month", "day"]])
    df["date"] = df["date"].dt.date
    df = df.drop(["year", "month", "day"], axis=1)
    df = add_missing_working_days(df, year=year, month=month)

    df["weekday"] = pd.to_datetime(df["date"]).dt.day_name()
    return df


def summary(df: pd.DataFrame, scheduled_hours: int):
    _summary = (
        df.groupby("project")["time"]
        .sum()
        .sort_values(ascending=False)
        .astype(int)
        .reset_index()
    )

    _summary = _summary.append(
        pd.DataFrame(
            {
                "project": ["Total"],
                "time": f"{int(_summary['time'].sum())}/{scheduled_hours}",
            }
        )
    )
    return _summary


def hours(df: pd.DataFrame, scheduled_hours: int) -> pd.DataFrame:
    df = df[["weekday", "date", "project", "time"]].copy()
    total = df["time"].fillna(0).sum().astype(int)
    total_row = pd.DataFrame(
        {
            "date": [""],
            "project": "Total",
            "time": f"{total}/{scheduled_hours}",
        }
    )

    df = df.append(total_row)
    return df


def print_table_df(df: pd.DataFrame):
    table = Table(header_style="bold blue")
    for column in df.columns:
        table.add_column(column, justify="right", style="dim")
    for row in df.itertuples():
        table.add_row(*[str(i) for i in row[1:]])
    console.print(table)


def main():
    args = parse_args()
    x3 = X3()

    console.print("Loading...")
    geldig = x3.geldig(year=args.year, month=args.month)
    console.print("✓", style="bold green", end=" ")
    console.print("geldig")
    lines = x3.lines(year=args.year, month=args.month)
    console.print("✓", style="bold green", end=" ")
    console.print("lines")
    illness = x3.illness(year=args.year, month=args.month)
    console.print("✓", style="bold green", end=" ")
    console.print("illness", end="\n\n")

    df = create_df(lines, geldig, year=args.year, month=args.month)
    console.print("Summary:", style="bold white")
    print_table_df(summary(df, scheduled_hours=geldig["scheduleHours"]))
    console.print("Hours", style="bold white")
    print_table_df(hours(df, scheduled_hours=geldig["scheduleHours"]).fillna("-"))
    print()


if __name__ == "__main__":
    main()
