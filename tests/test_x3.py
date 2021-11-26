import pytest

from x3cli.x3 import X3


@pytest.fixture()
def x3():
    _x3 = X3()
    return _x3


def test_x3_login():
    x3 = X3()
    assert False


def test_x3_geldig(x3):
    expected_keys = {
        "allowApproveMonth",
        "lastApproved",
        "monthIsApproved",
        "projects",
        "scheduleHours",
    }

    json = x3.geldig(year=2021, month=11)

    assert json.keys() == expected_keys
    assert len(json["projects"]) > 1  # when not logged in, you only get one


def test_x3_illness(x3):
    expected_keys = {"currentIllness", "nextIllness"}

    json = x3.illness(year=2021, month=11)

    assert json.keys() == expected_keys


def test_x3_lines(x3):
    year = 2021
    month = 11
    lines = x3.lines(year=year, month=month)
    assert len(lines) > 0, f"No lines found, are you sure you have hours for year {year} and month {month}?"
