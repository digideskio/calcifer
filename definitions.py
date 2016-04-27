from abc import ABCMeta, abstractmethod

class Definition:
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_template(self):
        pass

    @abstractmethod
    def match(self, value):
        pass

    def __repr__(self):
        return "Definition()"

class Value(Definition):
    def __init__(self, value):
        self._value = value

    @property
    def value(self):
        return self._value

    def match(self, value):
        return (self.value == value, self)

    def get_template(self):
        return self.value

    def __repr__(self):
        return (
            "Value(value={})"
        ).format(self.value)

    def __eq__(self, other):
        return (
            isinstance(other, Value) and other.value == self.value
        )


class Field(Definition):
    def __init__(self, field_type=None, **params):
        self._params = params
        if field_type:
            self._params['type'] = field_type
        if 'required' not in params:
            self._params['required'] = False

    @property
    def params(self):
        return self._params

    @property
    def value(self):
        return self._params.get('value')

    def get_template(self):
        return self.params

    def match(self, value):
        if 'value' in self.params:
            return (self.params['value'] == value, self)

        new_params = {k: v for k, v in self.params.items()}
        new_params['value'] = value
        return (True, Field(**new_params))

    def __repr__(self):
        args = ['{}={}'.format(k, v) for k, v in self.params.items()]
        return "Field({})".format(", ".join(args))

    def __eq__(self, other):
        return (
            isinstance(other, Field) and other.params == self.params
        )
