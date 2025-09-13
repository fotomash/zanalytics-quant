import pytest
from utils.import_utils import get_function_from_string
import math

def test_get_function_from_string():
    sqrt = get_function_from_string("math.sqrt")
    assert sqrt(9) == 3

def test_get_function_from_string_import_error():
    with pytest.raises(ImportError):
        get_function_from_string("nonexistent_module.func")

def test_get_function_from_string_attribute_error():
    with pytest.raises(AttributeError):
        get_function_from_string("math.nonexistent_func")

def test_get_function_from_string_type_error():
    with pytest.raises(TypeError):
        get_function_from_string("math.pi") # math.pi is an attribute, not a callable function

def test_get_function_from_string_value_error_no_function_name():
    # The current implementation will raise a ValueError if no function name is provided
    with pytest.raises(ValueError, match="not enough values to unpack"):
        get_function_from_string("math")

def test_get_function_from_string_with_multiple_args():
    # Create a dummy function for testing multiple arguments
    def add(a, b):
        return a + b

    # Temporarily add 'add' to math module for testing purposes
    # This is a bit hacky, but for testing purposes it's acceptable
    # In a real scenario, you might create a dummy module or use a mock
    setattr(math, 'add', add)
    add_func = get_function_from_string("math.add")
    assert add_func(2, 3) == 5
    delattr(math, 'add') # Clean up

def test_get_function_from_string_no_args():
    # Create a dummy function for testing no arguments
    def hello():
        return "Hello"

    setattr(math, 'hello', hello)
    hello_func = get_function_from_string("math.hello")
    assert hello_func() == "Hello"
    delattr(math, 'hello') # Clean up
