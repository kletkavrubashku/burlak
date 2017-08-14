from cocaine.burlak import burlak

import pytest

from tornado import queues

from .common import ASYNC_TESTS_TIMEOUT, \
    make_logger_mock, make_mock_channel_with


to_stop_apps = [
    ['app3', 'app4', 'app5', 'app6', 'app7'],
    ['app2', 'app3'],
    ['app3'],
]

to_run_apps = [
    dict(run3=burlak.StateRecord(3, 't1')),
    dict(
        run2=burlak.StateRecord(2, 't2'),
        run3=burlak.StateRecord(3, 't3'),
        run4=burlak.StateRecord(4, 't4')
    ),
    dict(
        run3=burlak.StateRecord(3, 't3'),
        run4=burlak.StateRecord(4, 't4'),
        run5=burlak.StateRecord(5, 't5'),
        run6=burlak.StateRecord(6, 't6'),
        run7=burlak.StateRecord(7, 't7')
    ),
]


@pytest.fixture
def elysium(mocker):
    node = mocker.Mock()
    node.start_app = mocker.Mock(return_value=make_mock_channel_with(0))
    node.pause_app = mocker.Mock(return_value=make_mock_channel_with(0))
    node.control = mocker.Mock(return_value=make_mock_channel_with(0))

    return burlak.AppsElysium(
        make_logger_mock(mocker), burlak.CommittedState(), node,
        queues.Queue(), 'none')


@pytest.mark.gen_test(timeout=ASYNC_TESTS_TIMEOUT)
def test_stop(elysium, mocker):
    stop_side_effect = [True for _ in to_stop_apps]
    stop_side_effect.append(False)

    mocker.patch.object(
        burlak.LoopSentry, 'should_run', side_effect=stop_side_effect)

    for stop_apps in to_stop_apps:
        yield elysium.control_queue.put(
            burlak.DispatchMessage(dict(), -1, False, set(stop_apps), set())
        )

    yield elysium.blessing_road()

    for apps_list in to_stop_apps:
        for app in apps_list:
            assert elysium.node_service.called_with(app)

    assert elysium.node_service.pause_app.call_count == \
        sum(map(len, to_stop_apps))


@pytest.mark.gen_test(timeout=ASYNC_TESTS_TIMEOUT)
def test_run(elysium, mocker):
    stop_side_effect = [True for _ in to_run_apps]
    stop_side_effect.append(False)

    mocker.patch.object(
        burlak.LoopSentry, 'should_run', side_effect=stop_side_effect)

    for run_apps in to_run_apps:
        yield elysium.control_queue.put(
            burlak.DispatchMessage(
                run_apps, -1, False, set(), set(run_apps.iterkeys()))
        )

    yield elysium.blessing_road()

    for apps_list in to_run_apps:
        for app, record in apps_list.iteritems():
            assert elysium.node_service.start_app.called_with(
                app,
                record.profile
            )

    assert \
        elysium.node_service.start_app.call_count == \
        sum(map(len, to_run_apps))

    assert elysium.node_service.control.call_count == \
        sum(map(len, to_run_apps))


@pytest.mark.gen_test(timeout=ASYNC_TESTS_TIMEOUT)
def test_control(elysium, mocker):
    stop_side_effect = [True for _ in to_run_apps]
    stop_side_effect.append(False)

    mocker.patch.object(
        burlak.LoopSentry, 'should_run', side_effect=stop_side_effect)

    for run_apps in to_run_apps:
        yield elysium.control_queue.put(
            burlak.DispatchMessage(
                run_apps, -1, True, set(), set(run_apps.iterkeys()))
        )

    yield elysium.blessing_road()

    for apps_list in to_run_apps:
        for app, record in apps_list.iteritems():
            assert elysium.node_service.start_app.called_with(
                app,
                record.profile
            )

            assert elysium.node_service.control.called_with(app)

    assert \
        elysium.node_service.start_app.call_count == \
        sum(map(len, to_run_apps))
    assert \
        elysium.node_service.control.call_count == \
        sum(map(len, to_run_apps))


@pytest.mark.gen_test(timeout=ASYNC_TESTS_TIMEOUT)
def test_gapped_control(elysium, mocker):
    '''Test for malformed state and to_run list combination'''
    stop_side_effect = [True for _ in to_run_apps]
    stop_side_effect.append(False)

    mocker.patch.object(
        burlak.LoopSentry, 'should_run', side_effect=stop_side_effect)

    gapped_states = []
    trig = 0
    for state in to_run_apps:
        trig ^= 1

        if trig:
            keys_to_preserve = list(state.keys())[0:-1]
        else:
            keys_to_preserve = list(state.keys())[1:]

        gapped_states.append({
            k: v
            for k, v in state.iteritems()
            if k in keys_to_preserve})

    for state, gap_state in zip(to_run_apps, gapped_states):
        yield elysium.control_queue.put(
            burlak.DispatchMessage(
                gap_state, -1, True, set(), set(state.iterkeys()))
        )

    yield elysium.blessing_road()

    for state in to_run_apps:
        for app, record in state.iteritems():
            assert elysium.node_service.start_app.called_with(
                app,
                record.profile
            )

    for state in gapped_states:
        for app, record in state.iteritems():
            assert elysium.node_service.control.called_with(app)

    assert \
        elysium.node_service.start_app.call_count == \
        sum(map(len, gapped_states))
    assert \
        elysium.node_service.control.call_count == sum(map(len, gapped_states))