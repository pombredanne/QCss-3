"""
Generic collector.

This module provides a generic collector which implements some useful
methods to be used by more specific collectors. It is not a complete
collector.
"""

from twisted.internet import defer

from qcss3.collector.datastore import LoadBalancer

class GenericCollector:
    """
    Helper functions for a collector.

    This generic collector needs several class variables:
     - C{oids} should be a mapping between OID names and numerical OID.
     - C{kind} should be a string defining the kind of load balancer
    """

    def __init__(self, config, proxy, name, description):
        self.config = config
        self.proxy = proxy
        self.lb = LoadBalancer(name, self.kind, description)

    def _extend_oids(self, *oids):
        newoids = []
        for o in oids:
            if type(o) is not tuple:
                newoids.append(self.oids[o])
            else:
                no = [self.oids[o[0]]]
                no.extend(o[1:])
                newoids.append(tuple(no))
        return tuple(newoids)

    def iscached(self, *oids):
        try:
            self.cache(*oids)
        except KeyError:
            return False
        return True

    @defer.inlineCallbacks
    def cache_or_get(self, *oids):
        try:
            defer.returnValue(self.cache(*oids))
        except KeyError:
            yield self.proxy.get(list(self._extend_oids(*oids)))
            defer.returnValue(self.cache(*oids))

    def cache(self, *oids):
        """
        Retrieve OID from proxy cache. First member of each provided
        OID is fetched from OID dictionary.
        """
        oids = self._extend_oids(*oids)
        return self.proxy.cache(*oids)

    def bitmap(self, bitmap):
        for i in range(len(bitmap)):
            if bitmap[i] == '\x00':
                continue
            for r in range(8):
                if not ord(bitmap[i]) & (1 << r):
                    continue
                r = 8-r + i*8
                yield r
