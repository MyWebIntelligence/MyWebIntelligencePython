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


def test_get_domain():
    """
    Test domain extraction from any url
    :return:
    """
    assert get_domain("https://www.domain.com/test.html") == "www.domain.com"


def test_remove_anchor():
    """
    Test anchor removing
    :return:
    """
    url = "http://www.example.com/path/to/doc.html"
    a = remove_anchor("http://www.example.com/path/to/doc.html#comments") == url
    b = remove_anchor("http://www.example.com/path/to/doc.html") == url
    assert a and b
