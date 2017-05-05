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
import os
from calcifer.tree import (
    PolicyNode, UnknownPolicyNode, LeafPolicyNode
)
from calcifer.zipper import Zipper


class Partial(object):
    def __init__(self, zipper=None):
        if zipper is None:
            zipper = Zipper([], UnknownPolicyNode())
        self.zipper = zipper

    @staticmethod
    def from_obj(obj):
        return Partial(
            Zipper([], PolicyNode.from_obj(obj))
        )

    @property
    def root(self):
        return self.zipper.root.node.value

    @property
    def path(self):
        return self.zipper.path

    @property
    def scope(self):
        return "/{}".format("/".join([str(step) for step in self.zipper.path]))

    @property
    def scope_value(self):
        node, _ = self.select(self.scope, set_path=False)
        return node.value

    def get_template(self):
        return self.zipper.root.node.get_template()

    def select(self, scope, set_path=True):
        """
        Select a node at a given scope, possibly setting the path on a newly returned
        partial.

        Cases:
            - If scope begins with "/", it's an absolute path
            - Otherwise, scope is a relative path, and the existing path should be subscoped
        """
        old_scope = self.scope

        if scope == "":
            scope = old_scope
        elif scope[0] != "/":
            scope = "{}/{}".format(old_scope, scope)

        relative_scope = os.path.relpath(scope, old_scope)
        if relative_scope == '.':
            relative_path = []
        else:
            relative_path = relative_scope.split('/')

        def maybe_coerce_to_int(step):
            try:
                return int(step)
            except ValueError:
                return step

        zipper = self.zipper
        undo_path = []
        for step in relative_path:
            if step == '..':
                zipper, undo_step = zipper.up()
            else:
                step = maybe_coerce_to_int(step)
                zipper = zipper.down(step)
                undo_step = '..'

            undo_path.insert(0, undo_step)

        node = zipper.node

        if not set_path:
            for step in undo_path:
                if step == '..':
                    zipper, _ = zipper.up()
                else:
                    zipper = zipper.down(step)

        return node, Partial(zipper)

    def define_as(self, definition):
        existing_value = self.scope_value
        if existing_value:
            valid, new_definition = definition.match(existing_value)
            if not valid:
                return (None, self)
            definition = new_definition

        new_zipper = self.zipper.set_node(LeafPolicyNode(definition))
        partial = Partial(new_zipper)
        return definition, partial

    def set_value(self, value, selector=None):
        partial = self
        if selector is not None:
            _, partial = partial.select(selector)
        new_zipper = partial.zipper.set_node(PolicyNode.from_obj(value))

        return (
            value, Partial(new_zipper)
        )

    def set_node(self, node):
        new_zipper = self.zipper.set_node(node)

        return (
            node, Partial(new_zipper)
        )

    def match(self, value):
        node, new_self = self.select("")
        matches, new_node = node.match(value)
        _, new_partial = new_self.set_node(new_node)
        if matches:
            return True, new_partial

        return False, self

    def __repr__(self):
        return "Partial(root={}, path={})".format(self.root, self.path)
