"""
`calcifer.partial` module

This module is used to provide the specific data structure used in the
stateful computation of command policy.

The data structure has two parts:
- a root policy node
- a pointer to a "current scope"

Operations are provided on Partial that allow the manipulation of either
the policy tree or the pointer, or both.
"""
from jsonpointer import JsonPointer

from calcifer.tree import (
    PolicyNode, UnknownPolicyNode, LeafPolicyNode
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
    def root(self):
        return self._root.value

    @property
    def path(self):
        return self._pointer.parts

    @property
    def scope(self):
        sel = self._pointer.path
        if not sel:
            sel = u'/'
        return sel

    @property
    def scope_value(self):
        node, _ = self.select(self.scope, set_path=False)
        return node.value

    def get_template(self):
        return self._root.get_template()

    @staticmethod
    def sub_scope(parent_abs='/', child_rel=''):
        rels = []
        if parent_abs == '/':
            rels.append('')
        else:
            rels += parent_abs.split('/')

        if child_rel:
            rels += child_rel.split('/')

        return '/'.join(rels)

    def select(self, selector, set_path=True):
        old_selector = self.scope
        old_path = self._pointer.parts

        if not selector:
            selector = old_selector
        elif selector[0] != '/':
            selector = self.sub_scope(old_selector, selector)

        if selector == '/':
            selector = ''

        selected_path = JsonPointer(selector).parts

        if set_path:
            new_path = selected_path
        else:
            new_path = old_path

        node, new_root = self._root.select(selected_path)
        return node, Partial(new_root, new_path)

    def define_as(self, definition):
        existing_value = self.scope_value
        if existing_value:
            valid, new_definition = definition.match(existing_value)
            if not valid:
                return (None, self)
            definition = new_definition

        return (
            definition, Partial(
                self._pointer.set(
                    self._root, LeafPolicyNode(definition), inplace=False
                ),
                path=self._pointer.parts
            )
        )

    def set_value(self, value, selector=None):
        if selector is not None:
            pointer = JsonPointer(selector)
        else:
            pointer = self._pointer

        return (
            value, Partial(
                pointer.set(
                    self._root, PolicyNode.from_obj(value), inplace=False
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
        _, new_partial = new_self.set_node(new_node)
        if matches:
            return True, new_partial

        return False, self

    def __repr__(self):
        return "Partial(root={}, path={})".format(self._root, self.path)
