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
from calcifer.tree import (
    PolicyNode, UnknownPolicyNode, LeafPolicyNode
)
from calcifer.zipper import Zipper


class Partial(object):
    def __init__(self, root=None, path=None):
        if root is None:
            root = UnknownPolicyNode()
        if path is None:
            path = []

        self.zipper = Zipper([], root).select(path)

    @staticmethod
    def from_obj(obj):
        return Partial(
            root=PolicyNode.from_obj(obj)
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

    def select(self, scope, set_path=True):
        """
        Select a node at a given scope, possibly setting the path on a newly returned
        partial.

        Cases:
            - If scope begins with "/", it's an absolute path
            - Otherwise, scope is a relative path, and the existing path should be subscoped
        """
        old_scope = self.scope
        old_path = self.zipper.path

        if not scope:
            scope = old_scope
        elif scope[0] != '/':
            scope = self.sub_scope(old_scope, scope)

        # scope should be absolute
        # convert scope to path

        # remove leading slash
        scope = scope[1:]
        if scope:
            selected_path = scope.split("/")  # to remove leading slash
        else:
            selected_path = []

        def maybe_coerce_to_int(step):
            try:
                return int(step)
            except ValueError:
                return step

        selected_path = [
            maybe_coerce_to_int(step) for step in selected_path
        ]

        new_zipper = self.zipper.root.select(selected_path)

        if set_path:
            new_path = selected_path
        else:
            new_path = old_path

        return new_zipper.node, Partial(new_zipper.root.node, new_path)

    def define_as(self, definition):
        existing_value = self.scope_value
        if existing_value:
            valid, new_definition = definition.match(existing_value)
            if not valid:
                return (None, self)
            definition = new_definition

        new_zipper = self.zipper.set_node(LeafPolicyNode(definition))
        partial = Partial(new_zipper.root.node, self.path)
        return definition, partial

    def set_value(self, value, selector=None):
        partial = self
        if selector is not None:
            _, partial = partial.select(selector)
        new_zipper = partial.zipper.set_node(PolicyNode.from_obj(value))

        return (
            value, Partial(new_zipper.root.node, path=self.path)
        )

    def set_node(self, node):
        new_zipper = self.zipper.set_node(node)

        return (
            node, Partial(new_zipper.root.node, path=self.path)
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
