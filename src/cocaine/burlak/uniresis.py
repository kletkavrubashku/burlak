'''Uniresis service proxy

Used mostly for debug purposes as a stub, until real uniresis would
be available.

Remove candidate.
'''

from cocaine.services import Service

from tornado import gen


class ResoursesProxy(object):
    @gen.coroutine
    def uuid(self):  # pragma: no cover
        raise NotImplementedError(
            'uuid method sould be defined in derived classes')


class UniresisProxy(ResoursesProxy):

    def __init__(self, endpoints, name):
        self.name = name
        self.uniresis = \
            Service(name, endpoints) if endpoints else Service(name)

    @property
    def service_name(self):
        return self.name

    @gen.coroutine
    def uuid(self):
        ch = yield self.uniresis.uuid()
        uuid = yield ch.rx.get()
        raise gen.Return(uuid)


class DummyProxy():
    '''Stub for resource proxy
    Used for local tests purposes
    '''

    COCAINE_TEST_UUID = 'SOME_UUID'

    def __init__(self, uuid=None):
        self._uuid = uuid if uuid else DummyProxy.COCAINE_TEST_UUID

    @property
    def service_name(self):
        return 'dumm_proxy'

    @gen.coroutine
    def uuid(self):
        raise gen.Return(self._uuid)


def catchup_an_uniresis(
    use_stub_uuid=None, endpoints=None, service_name='locator'):
    '''
    Note that former `service_name` was uniresis, which is deprecated now.
    '''

    if use_stub_uuid:
        return DummyProxy(use_stub_uuid)
    else:
        return UniresisProxy(endpoints, service_name)
