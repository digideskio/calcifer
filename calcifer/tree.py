"""
`calcifer.tree` module

This module implements a non-deterministic nested dictionary (tree).
The tree comprises leaf nodes, dict nodes, and "unknown nodes" -- nodes
which are known to exist but undefined beyond that.

Ultimately, the policy tree contains *definitions*, a higher-level abstraction
on "value": LeafPolicyNode uses the property `definition`, which may compare
to specific values or generate a template for procuring the value.
"""
from abc import ABCMeta, abstractmethod
import logging

from calcifer.definitions import Value

logger = logging.getLogger(__name__)


class PolicyNode:
    """
    Abstract class for node tree.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_template(self):
        """
        Generate the template for the node (recursively)
        """
        pass

    @abstractmethod
    def select(self, path=None):
        """
        Traverse the tree and retrieve a specific node with a given path.
        `select` retrieves existing nodes or populates default nodes based
        on path values.

        Returns a tuple of (selected_node, new_root)
        """
        if not path:
            return (self, self)

    @abstractmethod
    def match(self, value):
        """
        `match` compares a node with a given value, possibly returning an
        altered node in the process. For unknown nodes, this means populating
        the node with a leaf node defined as having that value.

        For nodes with a more complex definition, the behavior of `match`
        defers to the definition of the node.
        """
        return False, self

    @staticmethod
    def from_obj(obj):
        """
        To facilitate converting nested dict data structures, the static
        method `from_obj` recursively constructs a PolicyNode tree from
        an object
        """
        if isinstance(obj, PolicyNode):
            return obj
        if isinstance(obj, dict):
            return DictPolicyNode(**obj)
        if isinstance(obj, list):
            return ListPolicyNode(*obj)
        else:
            return LeafPolicyNode(Value(obj))


class UnknownPolicyNode(PolicyNode):
    def __init__(self):
        pass

    @property
    def value(self):
        return None

    def get_template(self):
        return {}

    def select(self, path=None):
        if not path:
            return (self, self)

        # recurse
        first = path[0]
        rest = path[1:]

        value, subpolicy = UnknownPolicyNode().select(rest)

        return value, DictPolicyNode(**{first: subpolicy })

    def match(self, value):
        return True, LeafPolicyNode(Value(value))

    def __repr__(self):
        return "UnknownPolicyNode()"

    def __eq__(self, other):
        return isinstance(other, UnknownPolicyNode)


class LeafPolicyNode(PolicyNode):
    def __init__(self, definition=None):
        self._definition = definition

    @property
    def definition(self):
        return self._definition

    @property
    def value(self):
        return self._definition.value

    def get_template(self):
        return self.definition.get_template()

    def select(self, path=None):
        if path:
            logger.debug((
                "Attempting to select sub-path %r of %r"
            ), path, self)
            raise Exception("Node cannot be traversed")

        return (self, self)

    def match(self, value):
        matches, new_definition = self.definition.match(value)
        return matches, LeafPolicyNode(new_definition)

    def __repr__(self):
        return (
            "LeafPolicyNode("
            "definition={definition}"
            ")"
        ).format(definition=self.definition)

    def __eq__(self, other):
        return (
            isinstance(other, LeafPolicyNode) and
            other.definition == self.definition
        )


class DictPolicyNode(PolicyNode):
    def __init__(self, **nodes):
        self._nodes = {
            k: PolicyNode.from_obj(v)
            for k, v in nodes.items()
        }

    @property
    def nodes(self):
        return self._nodes

    @property
    def keys(self):
        return self._nodes.keys()

    @property
    def value(self):
        return {
            name: node.value
            for name, node in self.nodes.items()
        }

    def get_template(self):
        return {
            k: v.get_template() for k, v in self.nodes.items()
        }

    def select(self, path=None):
        if not path:
            return (self, self)

        first = path[0]
        rest = path[1:]

        node, new_first = self[first].select(rest)
        new_nodes = {k: v for k, v in self.nodes.items()}
        new_nodes[first] = new_first

        return node, DictPolicyNode(**new_nodes)

    def match(self, value):
        return False, self

    def __setitem__(self, key, node):
        self._nodes[key] = node

    def __getitem__(self, key):
        if key not in self._nodes:
            return UnknownPolicyNode()
        return self._nodes[key]

    def __repr__(self):
        args = ['{}={}'.format(k, v) for k, v in self.nodes.items()]
        return "DictPolicyNode({})".format(", ".join(args))

    def __eq__(self, other):
        return (
            isinstance(other, DictPolicyNode) and
            other.nodes == self.nodes
        )

class ListPolicyNode(PolicyNode):
    def __init__(self, *nodes):
        self._nodes = [
            PolicyNode.from_obj(v)
            for v in nodes
        ]

    @property
    def nodes(self):
        return self._nodes

    @property
    def keys(self):
        return [str(key) for key in range(len(self._nodes))]

    @property
    def value(self):
        return [
            node.value
            for node in self.nodes
        ]

    def get_template(self):
        return [
            v.get_template() for v in self.nodes
        ]

    def select(self, path=None):
        if not path:
            return (self, self)

        first = int(path[0])

        rest = path[1:]

        node, new_first = self[first].select(rest)
        new_nodes = [v for v in self.nodes]
        new_nodes[first] = new_first

        return node, ListPolicyNode(*new_nodes)

    def match(self, value):
        return False, self

    def __setitem__(self, key, node):
        key = int(key)
        sparsity = key - len(self._nodes) + 1
        self._nodes.extend([UnknownPolicyNode()] * sparsity)
        self._nodes[key] = node

    def __getitem__(self, key):
        try:
            key = int(key)
            return self._nodes[int(key)]
        except:
            return UnknownPolicyNode()

    def __repr__(self):
        args = ['{}'.format(v) for v in self.nodes]
        return "ListPolicyNode({})".format(", ".join(args))

    def __eq__(self, other):
        return (
            isinstance(other, ListPolicyNode) and
            other.nodes == self.nodes
        )
