from utils.import_utils import get_function_from_string


def test_get_function_from_string():
    sqrt = get_function_from_string("math.sqrt")
    assert sqrt(9) == 3
