from cocaine.burlak import burlak, config
from cocaine.burlak.context import Context, LoggerSetup
from cocaine.burlak.sharding import ShardingSetup
from cocaine.burlak.uniresis import catchup_an_uniresis

import pytest

from tornado import queues

from .common import ASYNC_TESTS_TIMEOUT
from .common import make_future, make_logger_mock, make_mock_channel_with


TEST_UUID_PFX = '/test_uuid_prefix'
TEST_UUID = 'test_uuid1'

apps_lists = [
    ('app1', 'app2', 'app3'),
    ('app3', 'app4', 'app5'),
    ('app5', 'app6'),
]

apps_lists_ecxpt = [
    Exception('some', 'error0'),
    ('app2', 'app3'),
    Exception('some', 'error1'),
    ('app3', 'app4'),
    Exception('some', 'error2'),
]

states_list = [
    (dict(
        app1=dict(workers=1, profile='SomeProfile1'),
        app2=dict(workers=2, profile='SomeProfile2'),
        app3=dict(workers=3, profile='SomeProfile3'),
    ), 0),
    (dict(
        app3=dict(workers=3, profile='SomeProfile3'),
        app4=dict(workers=4, profile='SomeProfile4'),
        app5=dict(workers=5, profile='SomeProfile5'),
    ), 1),
]


states_list_broken = [
    (dict(
        app2=dict(workers=3, profile='SomeProfile3'),
        app3=dict(workers1='hello', profile='SomeProfile3'),
    ), 1),
    (dict(
        app3=dict(workers=3, profile='SomeProfile3'),
        app4=dict(workers='broken', profile=1),
    ), 2),
    (dict(
        app3=dict(workers=3, profile='SomeProfile3'),
        app5=dict(workers=10, profiles=2, profile='z'),
    ), 3),
]


@pytest.fixture
def acq(mocker):
    logger = make_logger_mock(mocker)
    input_queue = queues.Queue()

    sentry_wrapper = mocker.Mock()

    context = Context(
        LoggerSetup(logger, False),
        config.Config(mocker.Mock()),
        '0',
        sentry_wrapper,
        mocker.Mock(),
    )

    uniresis = catchup_an_uniresis(context, use_stub_uuid=TEST_UUID)
    sharding_setup = ShardingSetup(context, uniresis)
    return burlak.StateAcquirer(context, sharding_setup, input_queue)


@pytest.mark.gen_test(timeout=ASYNC_TESTS_TIMEOUT)
def test_state_subscribe_input(acq, mocker):
    stop_side_effect = [True for _ in states_list]
    stop_side_effect.append(True)
    stop_side_effect.append(False)

    mocker.patch.object(
        burlak.LoopSentry, 'should_run', side_effect=stop_side_effect)

    unicorn = mocker.Mock()
    unicorn.subscribe = mocker.Mock(
        side_effect=[make_mock_channel_with(*states_list)]
    )

    init_state = True  # `uuid` first message
    for state, ver in states_list:
        yield acq.subscribe_to_state_updates(unicorn)

        if init_state:
            inp = yield acq.input_queue.get()
            acq.input_queue.task_done()

            assert isinstance(inp, burlak.DumpCommittedState)

            init_state = False

        inp = yield acq.input_queue.get()
        acq.input_queue.task_done()

        assert isinstance(inp, burlak.StateUpdateMessage)

        awaited_state = {
            app: burlak.StateRecord(val['workers'], val['profile'])
            for app, val in state.iteritems()
        }

        assert inp.state == awaited_state
        assert inp.version == ver


@pytest.mark.gen_test(timeout=ASYNC_TESTS_TIMEOUT)
def test_state_broken_input(acq, mocker):
    ln = len(states_list_broken) * 2

    stop_side_effect = [True for _ in xrange(0, ln)]
    stop_side_effect.append(False)

    mocker.patch.object(
        burlak.LoopSentry, 'should_run', side_effect=stop_side_effect)
    mocker.patch('tornado.gen.sleep', return_value=make_future(0))

    unicorn = mocker.Mock()
    unicorn.subscribe = mocker.Mock(
        side_effect=[make_mock_channel_with(*states_list_broken)]
    )

    acq.input_queue = mocker.Mock()
    acq.input_queue.put = mocker.Mock(return_value=make_future(0))

    cnt = 0
    for state, ver in states_list_broken:
        yield acq.subscribe_to_state_updates(unicorn)
        cnt += 1

    assert cnt == len(states_list_broken)
