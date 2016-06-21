from calcifer.operators import (
    regarding, set_value, select, unit_value,
)

def add_error(error):
    return select("/errors") >> unit_value >> (
        lambda errors: regarding("/errors", set_value(errors + [error]))
    )

