from calcifer.operators import (
    regarding, append_value,
)

def add_error(error):
    return regarding("/errors", append_value(error))
