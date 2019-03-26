import pytest
from argparse import ArgumentParser
from mwi.core import *


def test_check_args_missing_mandatory():
    """
    Tests that check_args raises Exception if mandatory args are missing
    :return:
    """
    parser = ArgumentParser()
    parser.add_argument("-a", action="store_true")
    parser.add_argument("-c", action="store_true")
    args = parser.parse_args(["-a", "-c"])
    with pytest.raises(Exception):
        check_args(args, ("a", "b"))
    assert True
