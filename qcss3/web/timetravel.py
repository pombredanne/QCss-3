"""
Past handling resources
"""

import re
from zope.interface import Interface
from twisted.python import log
from nevow import rend, flat, tags as T, loaders
from nevow import inevow

class IPastDate(Interface):
    """Remember a past date for time travel"""
    pass

class PastConnectionPool:
    """
    Proxy for an existing connection pool to run queries in the past.

    This proxy intercepts C{runQueryInPast} and modifies the request to
    make it happen in the past (if necessary). It only accepts simple
    queries (query + dict) and needs a web context (to extract the
    date).
    """

    _regexp_deleted = re.compile(r"(?:(\w+)\.|)deleted\s*=\s*'infinity'")
    _regexp_full = re.compile(r"\B_full\b")

    def __init__(self, orig):
        self._orig = orig

    def __getattr__(self, attribute):
        return getattr(self._orig, attribute)

    def runQueryInPast(self, ctx, query, dic=None):
        """
        Run the specified query in the past.

        Occurences of C{deleted='infinity'} are replaced by C{(created
        < %(__date)s AND deleted > %(__date)s)}
        """

        def convert(date, mo):
            if mo.group(1):
                suffix = "%s." % mo.group(1)
            else:
                suffix = ""
            return " AND ".join(['(%screated < %%(__date)s::abstime' % suffix,
                                 '%sdeleted > %%(__date)s::abstime)' % suffix])

        # Try to get the date from the context
        try:
            date = ctx.locate(IPastDate)
        except KeyError:
            # No in the past
            query = PastConnectionPool._regexp_full.sub("", query)
            if dic:
                return self._orig.runQuery(query, dic)
            else:
                return self._orig.runQuery(query)

        # We need to run this request in the past
        if not dic:
            dic = {}
        dic["__date"] = date
        q = PastConnectionPool._regexp_deleted.sub(
            lambda x: convert(date, x), query)
        return self._orig.runQuery(q, dic)

class PastResource(rend.Page):
    """
    This is a special resource that needs to be instanciated with
    another resource. This resource will register the date into the
    current context and use the given resource to handle the request.
    """

    addSlash = True
    docFactory = loaders.stan(T.html [ T.body [ T.p [ "Nothing here" ] ] ])

    def __init__(self, main):
        self.main = main
        rend.Page.__init__(self)

    def dateOk(self, ctx, date):
        # The given date is correct, insert it in the context
        ctx.remember(date, IPastDate)
        return self.main

    def badDate(self, ctx, date):
        log.msg("Got bad date: %r" % date)
        return UnknownDate()

    def childFactory(self, ctx, date):
        # We must validate the date (use runOperation to avoid proxy)
        d = self.main.dbpool.runOperation("SELECT %(date)s::abstime",
                                          {'date': date})
        d.addCallbacks(lambda x: self.dateOk(ctx, date),
                       lambda x: self.badDate(ctx, date))
        return d


class UnknownDate(rend.Page):
    """
    400 error page for an unknown date
    """
    addSlash = True
    docFactory = loaders.stan(T.html [ T.body [ T.h1 [ "Bad request" ],
                                                T.p [ "Unknown date" ] ] ])

    def locateChild(self, ctx, segments):
        request = inevow.IRequest(ctx)
        request.setResponseCode(400)
        return self, ()
