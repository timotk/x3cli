import pytest

from x3cli.x3 import X3


@pytest.fixture()
def x3(mocker):
    _x3 = X3()
    mocker.patch.object(_x3, 'is_authenticated', return_value=True)
    return _x3


def test_x3_login(x3):
    # Login is mocked!
    assert x3.is_authenticated()


def test_x3_geldig_multiple_projects(requests_mock, x3):
    expected_dict = {'projects': ["project1", "project2"],
                     "allowApproveMonth": [],
                     "lastApproved": [],
                     "monthIsApproved": [],
                     "scheduleHours": []}

    requests_mock.post("https://x3.nodum.io/json/geldig", json=expected_dict)

    # Json is returned as-is.
    actual_dict = x3.geldig(year=2021, month=11)
    assert actual_dict == expected_dict


def test_x3_geldig_single_project(requests_mock, x3):
    """One project is an indicator you are not logged-in, somehow.
    """
    requests_mock.post("https://x3.nodum.io/json/geldig", json={'projects': ["single-project"]})

    with pytest.raises(ValueError) as e:
        x3.geldig(year=2021, month=11)
        assert str(e) == "Only one project found, you are not logged in"


def test_x3_illness(requests_mock, x3):
    expected_dict = {"currentIllness": [], "nextIllness": []}
    requests_mock.post("https://x3.nodum.io/json/illness", json=expected_dict)

    # Json is returned as-is.
    actual_dict = x3.illness(year=2021, month=11)

    assert actual_dict == expected_dict


def test_x3_lines(requests_mock, x3):
    expected_dict = {"??": [], "!!": []}
    requests_mock.post("https://x3.nodum.io/json/fetchlines", json=expected_dict)

    lines = x3.lines(year=2021, month=11)

    assert lines == expected_dict
