import pytest
from mwi.core import *


def test_get_domain():
    """
    Test domain extraction from any url
    :return:
    """
    assert get_domain_name("https://www.domain.com/test.html") == "www.domain.com"


def test_remove_anchor():
    """
    Test anchor removing
    :return:
    """
    url = "http://www.example.com/path/to/doc.html"
    a = remove_anchor("http://www.example.com/path/to/doc.html#comments") == url
    b = remove_anchor("http://www.example.com/path/to/doc.html") == url
    assert a and b
