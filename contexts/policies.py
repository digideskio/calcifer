from dramafever.premium.services.policy import (
    policies, regarding, define_as, set_value, select, unit_value,
)

def add_field(name, definition):
    return regarding(
        "/fields/{}".format(name), define_as(definition)
    )


def add_fields(fields):
    return policies(*[
        add_field(name, definition)
        for name, definition in fields.items()
    ])

def add_values(selector, values):
    def add_value(name, value):
        return regarding(name, set_value(value))
    return regarding(
        selector,
        *[add_value(name, value) for name, value in values.items()]
    )

def add_error(error):
    return select("/errors") >> unit_value >> (lambda errors:
        regarding("/errors", set_value(errors + [error]))
    )

def field_selector(field_name):
    return "/fields/{}".format(field_name)

