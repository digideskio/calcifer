import copy
import logging

from calcifer.contexts import Context
from calcifer.partial import Partial
from calcifer.operators import unless_errors

logger = logging.getLogger(__name__)


class BasePolicy(object):
    ctx_class = Context

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            method = args[0]
            self(method)

        self.includes = kwargs.get('includes', [])
        self.bind_ref = kwargs.get('bind_ref', False)
        self.args = []

    def __call__(self, method):
        if not hasattr(self, 'method'):
            self.method = method
        return self

    def __get__(self, obj, cls=None):
        self.parent = obj
        return self

    def using(self, *args):
        new_self = copy.deepcopy(self)
        new_self.args = args
        return new_self

    defaults = {
    }

    def initial_partial(self, obj=None):
        if obj is None:
            obj = {}

        for k, v in self.__class__.defaults.items():
            if k not in obj:
                obj[k] = v

        return Partial.from_obj(obj)

    def run(self, obj):
        new_self = copy.deepcopy(self)

        new_self.ref = obj
        ctx = new_self.context
        policy_rule = ctx.finalize()

        partial = new_self.initial_partial(obj)
        results = [
            new_self.resolve(final) for _, final in policy_rule.run(partial)
        ]

        return results

    def include(self, other):
        new_self = copy.deepcopy(self)
        new_self.includes.append(other)
        return new_self

    @staticmethod
    def resolve(final):
        return final

    @property
    def context(self):
        ctx_class = self.__class__.ctx_class
        ctx = ctx_class(
            name=getattr(self.method, "__name__", None)
        )
        method_args = [ctx]
        if self.bind_ref:
            method_args.append(self.ref)
        method_args += self.args
        self.method(*method_args)
        if getattr(self, 'parent', None):
            # TODO this is a codesmell
            logger.debug("context name: %s", ctx.ctx_name)
            if ctx.ctx_name == 'endpoint_policy':
                ctx.wrapper = lambda policy_rules: unless_errors(*policy_rules)

            includes = copy.copy(self.includes)
            for include in includes:
                if isinstance(include, str):
                    policy = getattr(self.parent, include)
                else:
                    policy = include
                if hasattr(self, 'ref'):
                    policy.ref = self.ref
                policy.args = self.args
                ctx.append(policy.context.finalize())
        return ctx


class DefaultPolicy(BasePolicy):
    def resolve(self, final):
        return {k:v for k,v in final.root.items() if k != 'context'}
