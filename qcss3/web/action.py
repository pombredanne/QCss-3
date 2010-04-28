"""
Action related pages
"""

from twisted.internet import defer
from twisted.python import log

from qcss3.web.timetravel import IPastDate
from qcss3.web.json import JsonPage
from qcss3.web.refresh import RefreshMixIn

class ActionMixIn:
    """
    Action related stuff to add actions to some resources.

    This mixin adds a decorator that should be used to add actions to
    a JSON resource. It also includes a child factory to execute
    actions. Therefore, it should be used before any other class that
    would define L{childFactory}.
    """

    @classmethod
    def actions(cls, f):
        """
        Decorator to add actions to a dictionary.

        This decorator should only be used on a function whose first
        argument is a context (since this context is needed to
        conditionnaly add actions)

        For example::
           { 'enable': 'Enable',
             'operenable': 'Enable (oper)' }

        This dictionary is added with the key C{actions}.
        """

        def wrapped(self, ctx, *args, **kwargs):

            def error(x, e):
                log.msg("unable to get actions for %r (%r): %s" % (self.lb, x, e.value))
                return x

            def update(x, y):
                if y:
                    x['actions'] = y
                return x

            def add(x):
                # If in the past, don't add anything
                try:
                    date = ctx.locate(IPastDate)
                    return x
                except KeyError:
                    pass
                # If not a dictionary, don't add anything
                if type(x) is not dict:
                    return x
                # Otherwise, retrive list of actions
                if hasattr(self, "rs"):
                    d = self.collector.actions(self.lb, self.vs, self.rs)
                elif hasattr(self, "vs"):
                    d = self.collector.actions(self.lb, self.vs)
                else:
                    d = self.collector.actions(self.lb)
                d.addCallbacks(lambda y: update(x, y),
                               lambda e: error(x, e))
                return d

            d = defer.maybeDeferred(f, self, ctx, *args, **kwargs)
            d.addCallback(lambda x: add(x))
            return d

        return wrapped

    def childFactory(self, ctx, action):
        """
        Execute an action
        """
        vs = hasattr(self, "vs") and self.vs or None
        rs = hasattr(self, "rs") and self.rs or None
        sorry = False
        sorry = hasattr(self, "sorry") and self.sorry
        return ActionExecuteResource(self.dbpool, self.collector,
                                     self.lb, vs, rs, sorry,
                                     action)

class ActionExecuteResource(JsonPage, RefreshMixIn):
    """
    Execute an action for a given entity
    """

    def __init__(self, dbpool, collector, lb, vs, rs, sorry, action):
        self.dbpool = dbpool
        self.collector = collector
        self.lb = lb
        self.vs = vs
        self.rs = rs
        self.sorry = sorry
        self.action = action

    @RefreshMixIn.exist
    def data_json(self, ctx, data):
        return self.collector.actions(self.lb, self.vs, self.rs, self.action)
