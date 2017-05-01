"""
HERE THERE BE DRAGONS
"""
from calcifer.tree import UnknownPolicyNode


class Zipper(object):
    def __init__(self, breadcrumbs, node=None):
        """
        Initialize a zipper
        It takes two arguments:
            - breadcrumbs is a list of Breadcrumb objects
            - node is a PolicyNode
        """
        self.breadcrumbs = breadcrumbs
        if node is None:
            node = UnknownPolicyNode()
        self.node = node

    @property
    def root(self):
        new_zipper = self
        for _ in range(len(self.breadcrumbs)):
            new_zipper = new_zipper.up()
        return new_zipper

    @property
    def path(self):
        mapped_crumbs = list(map(lambda breadcrumb: breadcrumb.step_taken, self.breadcrumbs))
        return list(reversed(mapped_crumbs))

    def select(self, path):
        new_zipper = self
        for step in path:
            new_zipper = new_zipper.down(step)
        return new_zipper

    def down(self, step):
        chosen_node, new_node, steps_not_taken = self.node.choose(step)
        new_breadcrumbs = [Breadcrumb(step, new_node, steps_not_taken)] + self.breadcrumbs
        return Zipper(new_breadcrumbs, chosen_node)

    def set_node(self, node):
        return Zipper(self.breadcrumbs, node)

    def up(self):
        first = self.breadcrumbs[0]
        rest = self.breadcrumbs[1:]

        possible_steps = {first.step_taken: self.node}
        possible_steps.update(first.steps_not_taken)

        empty_parent = first.from_node
        new_node = empty_parent.reconstruct(possible_steps)

        return Zipper(rest, new_node)


class Breadcrumb(object):
    def __init__(self, step_taken, from_node, steps_not_taken=None):
        self.step_taken = step_taken
        self.from_node = from_node
        if steps_not_taken is None:
            steps_not_taken = {}
        self.steps_not_taken = steps_not_taken
