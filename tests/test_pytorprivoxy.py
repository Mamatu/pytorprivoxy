import main
import time

from pylibcommons import libprint
from private.lib import is_port_open

import logging
log = logging.getLogger('pytorprivoxy')

import os
TEST_LOG_LEVEL = os.environ.get("TEST_LOG_LEVEL")
if TEST_LOG_LEVEL is None:
    TEST_LOG_LEVEL = "DEBUG"

TEST_DELAY_BETWEEN = os.environ.get("TEST_DELAY_BETWEEN")
if TEST_DELAY_BETWEEN is None:
    TEST_DELAY_BETWEEN = 10
else:
    TEST_DELAY_BETWEEN = int(TEST_DELAY_BETWEEN)

TEST_INITIALIZATION_TIMEOUT = os.environ.get("TEST_INITIALIZATION_TIMEOUT")
if TEST_INITIALIZATION_TIMEOUT is None:
    TEST_INITIALIZATION_TIMEOUT = 120
else:
    TEST_INITIALIZATION_TIMEOUT = int(TEST_INITIALIZATION_TIMEOUT)

import psutil

PIDS = []
def teardown_function(function):
    global PIDS
    libprint.print_func_info(logger = log.info)
    time.sleep(TEST_DELAY_BETWEEN)
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            for pid in PIDS:
                if pid == proc.info['pid']:
                    raise Exception(f"Process is still running: {proc.info}")
            if 'tor' == proc.info['name']:
                raise Exception(f"Tor process is still running: {proc.info}")
            if 'privoxy' == proc.info['name']:
                raise Exception(f"Privoxy process is still running: {proc.info}")
    finally:
        PIDS = []

def while_with_timeout(timeout, condition, timeout_msg = None, time_sleep = 0.1):
    start_time = time.time()
    timeouted = False
    while condition():
        if time.time() - start_time >= timeout:
            timeouted = True
            break
        time.sleep(time_sleep)
    if timeouted:
        if timeout_msg is None:
            timeout_msg = "Timeout in while"
        raise Exception(timeout_msg)

def test_interrupt_initialization():
    global PIDS
    libprint.set_global_string("test_interrupt_initialization")
    assert is_port_open(9000)
    assert is_port_open(9001)
    assert is_port_open(9002)
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    pids = []
    def callback(ctx, stop_control):
        time.sleep(15)
        PIDS = ctx.get_pids()
        ctx.stop_all()
        stop_control.stop()
    thread = main.start_main_async(callback, log_level = TEST_LOG_LEVEL, start = (9000, 9001, 9002), stdout = True)
    libprint.print_func_info(logger = log.info)
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= 20

def test_initialize():
    libprint.set_global_string("test_initialize")
    assert is_port_open(9000)
    assert is_port_open(9001)
    assert is_port_open(9002)
    assert is_port_open(9003)
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    ports = (9000, 9001, 9002)
    def callback(ctx, stop_control):
        _cond = lambda: not len(ctx.instances) == 1
        while_with_timeout(2, _cond, timeout_msg = "No instance found")
        assert len(ctx.instances) == 1
        instance = ctx.instances[0]
        timeout_msg = f"instance.is_ready: {instance.is_ready()} server: {ctx.server}"
        PIDS = ctx.get_pids()
        while_with_timeout(TEST_INITIALIZATION_TIMEOUT, lambda: not instance.is_ready() or not ctx.server, timeout_msg = timeout_msg)
        ctx.stop_all()
        stop_control.stop()
    thread = main.start_main_async(callback, log_level = TEST_LOG_LEVEL, start = ports, server_port = 9003, stdout = True)
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= TEST_INITIALIZATION_TIMEOUT

def _get_ip_address(data):
    try:
        import json
        data = json.loads(data)
        import ipaddress
        return ipaddress.ip_address(data['origin'])
    except Exception as e:
        return None

def test_checkip():
    libprint.set_global_string("test_checkip")
    server_port = 9003
    assert is_port_open(9000)
    assert is_port_open(9001)
    assert is_port_open(9002)
    assert is_port_open(server_port)
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    ports = (9000, 9001, 9002)
    def callback(ctx, stop_control):
        _cond = lambda: not len(ctx.instances) == 1
        while_with_timeout(2, _cond, timeout_msg = "No instance found")
        instance = ctx.instances[0]
        _cond1 = lambda: not instance.is_ready() or not ctx.server
        PIDS = ctx.get_pids()
        while_with_timeout(TEST_INITIALIZATION_TIMEOUT, _cond1, timeout_msg = "Not ready")
        from multiprocessing.connection import Client
        with Client(("localhost", server_port)) as client:
            import json
            client.send("checkip 9002")
            data = client.recv()
            ipaddress = _get_ip_address(data)
            assert ipaddress != None
            client.send("stop")
        ctx.stop_all()
        stop_control.stop()
    thread = main.start_main_async(callback, log_level = TEST_LOG_LEVEL, start = ports, server_port = server_port, stdout = True)
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= TEST_INITIALIZATION_TIMEOUT

class IPAddressIdenticalException(Exception):
    def __init__(self, ipaddress1, ipaddress2):
        super().__init__(f"IP addresses are the same: {ipaddress1} {ipaddress2}")

def newnym_process(client):
    client.send("checkip 9002")
    data = client.recv()
    ipaddress1 = _get_ip_address(data)
    client.send("newnym 9001")
    data = client.recv()
    client.send("checkip 9002")
    data = client.recv()
    ipaddress2 = _get_ip_address(data)
    if ipaddress1 == ipaddress2:
        raise IPAddressIdenticalException(ipaddress1, ipaddress2)
    return ipaddress1, ipaddress2

def test_newnym():
    libprint.set_global_string("test_newnym")
    server_port = 9003
    assert is_port_open(9000)
    assert is_port_open(9001)
    assert is_port_open(9002)
    assert is_port_open(server_port)
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    main_async_kwargs = {"log_level": TEST_LOG_LEVEL, "start": (9000, 9001, 9002), "server_port": server_port, "stdout": True}
    def callback(ctx, stop_control):
        _cond = lambda: not len(ctx.instances) == 1
        while_with_timeout(2, _cond, timeout_msg = "No instance found")
        instance = ctx.instances[0]
        _cond1 = lambda: not instance.is_ready() or not ctx.server
        PIDS = ctx.get_pids()
        while_with_timeout(TEST_INITIALIZATION_TIMEOUT, _cond1, timeout_msg = "Not ready")
        from multiprocessing.connection import Client
        ip_addresses = None
        with Client(("localhost", server_port)) as client:
            _continue = True
            _count = 1
            while _continue and _count <= 5:
                try:
                    ip_addresses = newnym_process(client)
                    _continue = False
                except IPAddressIdenticalException as e:
                    _count = _count + 1
            libprint.print_func_info(logger = log.info, extra_string = f"IP: {ip_addresses} Count: {_count}")
            assert ip_addresses[0] != ip_addresses[1]
            client.send("stop")
        ctx.stop_all()
        stop_control.stop()
    thread = main.start_main_async(callback, **main_async_kwargs)
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= TEST_INITIALIZATION_TIMEOUT
    libprint.print_func_info(logger = log.info, prefix = "-")

def test_newnym_2_instances():
    libprint.set_global_string("test_newnym_2_instances")
    server_port = 9006
    assert is_port_open(9000), "9000"
    assert is_port_open(9001), "9001"
    assert is_port_open(9002), "9002"
    assert is_port_open(9003), "9003"
    assert is_port_open(9004), "9004"
    assert is_port_open(9005), "9005"
    assert is_port_open(server_port), f"{server_port}"
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    ports = [[9000, 9001, 9002], [9003, 9004, 9005]]
    main_async_kwargs = {"log_level": TEST_LOG_LEVEL, "start": ports, "server_port": server_port, "stdout": True}
    def callback(ctx, stop_control):
        while_with_timeout(2, lambda: not len(ctx.instances) == 2, timeout_msg = "main.get_count_of_instances() != 2")
        instance1 = ctx.instances[0]
        instance2 = ctx.instances[1]
        _cond = lambda: not instance1.is_ready() or not instance2.is_ready() or not ctx.server
        PIDS = ctx.get_pids()
        log_string = f"Not ready {instance1.is_ready()} {instance2.is_ready()} {ctx.server}"
        while_with_timeout(TEST_INITIALIZATION_TIMEOUT, _cond, timeout_msg = log_string)
        from multiprocessing.connection import Client
        ip_addresses = None
        with Client(("localhost", server_port)) as client:
            _continue = True
            _count = 1
            while _continue and _count <= 5:
                try:
                    ip_addresses = newnym_process(client)
                    _continue = False
                except IPAddressIdenticalException as e:
                    _count = _count + 1
            libprint.print_func_info(logger = log.info, extra_string = f"IP: {ip_addresses} Count: {_count}")
            assert ip_addresses[0] != ip_addresses[1]
        ctx.stop_all()
        stop_control.stop()
    thread = main.start_main_async(callback, **main_async_kwargs)
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= TEST_INITIALIZATION_TIMEOUT
