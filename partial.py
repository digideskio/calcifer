"""
`dramafever.premium.services.policy.partial` module

This module is used to provide the specific data structure used in the
stateful computation of command policy.

The data structure has two parts:
- a root policy node
- a pointer to a "current scope"

Operations are provided on Partial that allow the manipulation of either
the policy tree or the pointer, or both.
"""
from jsonpointer import JsonPointer

from dramafever.premium.services.policy.tree import (
    PolicyNode, UnknownPolicyNode, LeafPolicyNode, Value
)

class Partial(object):
    def __init__(self, root=None, path=None):
        if root is None:
            root = UnknownPolicyNode()
        if path is None:
            path = []

        self._root = root
        self._pointer = JsonPointer.from_parts(path)

    @staticmethod
    def from_obj(obj):
        return Partial(
            root=PolicyNode.from_obj(obj)
        )

    @property
    def path(self):
        return self._pointer.parts

    def get_template(self):
        return self._root.get_template()

    def select(self, selector, set_path=True):
        old_selector = self._pointer.path
        old_path = self._pointer.parts

        if not selector:
            selector = old_selector
        elif selector[0] != '/':
            selector = "{}/{}".format(old_selector, selector)

        selected_path = JsonPointer(selector).parts

        if set_path:
            new_path = selected_path
        else:
            new_path = old_path

        node, new_root = self._root.select(selected_path)
        return node, Partial(new_root, new_path)

    def set_path(self, path=None):
        if path is None:
            path = []
        _, new_item = self.select(JsonPointer.from_parts(path).path)
        return (
            None, new_item
        )

    def define_as(self, definition):
        return (
            definition, Partial(
                self._pointer.set(
                    self._root, LeafPolicyNode(definition), inplace=False
                ),
                path=self._pointer.parts
            )
        )

    def set_value(self, value):
        return (
            value, Partial(
                self._pointer.set(
                    self._root, LeafPolicyNode(Value(value)), inplace=False
                ),
                path=self._pointer.parts
            )
        )

    def set_node(self, node):
        return (
            node, Partial(
                self._pointer.set(self._root, node, inplace=False),
                path=self._pointer.parts
            )
        )

    def match(self, value):
        node, new_self = self.select("")
        matches, new_node = node.match(value)
        _, new_policy = new_self.set_node(new_node)
        if matches:
            return True, new_policy

        return False, self


    def __repr__(self):
        return "Partial(root={}, path={})".format(self._root, self.path)

