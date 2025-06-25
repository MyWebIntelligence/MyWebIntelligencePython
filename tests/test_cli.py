import pytest
from mwi.cli import *
from mwi.core import *
from argparse import ArgumentParser, Namespace
import random
import string


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
    options_str = get_arg_option('option_str', args, set_type=str, default='A')
    option_int = get_arg_option('option_int', args, set_type=int, default=5)
    assert type(options_str) is str \
        and options_str == 'A' \
        and type(option_int) is int \
        and option_int == 5

    options = {'option_str': '503', 'option_int': 3}
    args = Namespace(**options)
    options_str = get_arg_option('option_str', args, set_type=str, default='A')
    option_int = get_arg_option('option_int', args, set_type=int, default=5)
    assert type(options_str) is str \
        and options_str == '503' \
        and type(option_int) is int \
        and option_int == 3

    options = {'option_str': 503, 'option_int': '3'}
    args = Namespace(**options)
    options_str = get_arg_option('option_str', args, set_type=str, default='A')
    option_int = get_arg_option('option_int', args, set_type=int, default=5)
    assert type(options_str) is str \
        and options_str == '503' \
        and type(option_int) is int \
        and option_int == 3


def test_functional_test():
    letters = string.ascii_lowercase
    land_name = 'test_' + ''.join(random.choice(letters) for i in range(6))
    commands = [
            {'object': 'land', 'verb': 'create', 'name': land_name, 'desc': 'Test'},
            {'object': 'land', 'verb': 'addterm', 'land': land_name, 'terms': 'asthme, asthmatique, jeune, enfant, adolescent, nourrisson, bébé, nouveau-né'},
            {'object': 'land', 'verb': 'addurl', 'land': land_name, 'path': 'data/asthme-50.txt', 'urls': None},
            {'object': 'land', 'verb': 'list'},
            {'object': 'land', 'verb': 'crawl', 'name': land_name, 'limit': 2},
        {'object': 'land', 'verb': 'readable', 'name': land_name, 'limit': 1},
        {'object': 'domain', 'verb': 'crawl', 'limit': 2},
        {'object': 'land', 'verb': 'export', 'name': land_name, 'type': 'pagecsv', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': land_name, 'type': 'fullpagecsv', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': land_name, 'type': 'pagegexf', 'minrel': 1},
        {'object': 'land', 'verb': 'export', 'name': land_name, 'type': 'nodegexf', 'minrel': 1},
    ]
    for command in commands:
        args = Namespace(**command)
        ret = dispatch(args)
        assert ret == 1

def test_land_multi_language():
    """
    Test that creating a land with multiple languages stores the correct lang string.
    """
    from mwi import model
    land_name = 'test_multi_lang_' + ''.join(random.choice(string.ascii_lowercase) for _ in range(6))
    langs = ['fr', 'en', 'it']
    args = Namespace(object='land', verb='create', name=land_name, desc='Test multi lang', lang=langs)
    ret = dispatch(args)
    assert ret == 1
    land = model.Land.get_or_none(model.Land.name == land_name)
    assert land is not None
    assert land.lang == ','.join(langs)
