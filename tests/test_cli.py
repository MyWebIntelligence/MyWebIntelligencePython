import pytest
from mwi.cli import *
from argparse import ArgumentParser, Namespace


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


def test_get_arg_option():
    options = {'option_str': None, 'option_int': None}
    args = Namespace(**options)
    options_str = get_arg_option('option_str', args, typeof=str, default='A')
    option_int = get_arg_option('option_int', args, typeof=int, default=5)
    assert type(options_str) is str \
        and options_str == 'A' \
        and type(option_int) is int \
        and option_int == 5

    options = {'option_str': '503', 'option_int': 3}
    args = Namespace(**options)
    options_str = get_arg_option('option_str', args, typeof=str, default='A')
    option_int = get_arg_option('option_int', args, typeof=int, default=5)
    assert type(options_str) is str \
        and options_str == '503' \
        and type(option_int) is int \
        and option_int == 3

    options = {'option_str': 503, 'option_int': '3'}
    args = Namespace(**options)
    options_str = get_arg_option('option_str', args, typeof=str, default='A')
    option_int = get_arg_option('option_int', args, typeof=int, default=5)
    assert type(options_str) is str \
        and options_str == '503' \
        and type(option_int) is int \
        and option_int == 3


def test_functional_test():
    commands = [
        {'object': 'land', 'verb': 'create', 'name': 'test_asthme', 'desc': 'Asthme chez les jeunes'},
        {'object': 'land', 'verb': 'addterm', 'land': 'test_asthme', 'terms': 'asthme, asthmatique, jeune, enfant, adolescent, nourrisson, bébé, nouveau-né'},
        {'object': 'land', 'verb': 'addurl', 'land': 'test_asthme', 'path': 'data/asthme-50.txt', 'urls': None},
        {'object': 'land', 'verb': 'list'},
        {'object': 'land', 'verb': 'crawl', 'name': 'test_asthme', 'limit': 2},
        {'object': 'domain', 'verb': 'crawl', 'limit': 2},
        {'object': 'land', 'verb': 'export', 'name': 'test_asthme', 'type': 'pagecsv', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': 'test_asthme', 'type': 'pagegexf', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': 'test_asthme', 'type': 'nodegexf', 'minrel': 1},
    ]
    for command in commands:
        args = Namespace(**command)
        ret = dispatch(args)
        assert ret == 1
