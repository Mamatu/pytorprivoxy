import main
import time

from pylibcommons import libprint
from private.lib import is_port_open

import logging

def while_with_timeout(timeout, condition, timeout_msg = None, time_sleep = 0.1):
    start_time = time.time()
    timeouted = False
    libprint.print_func_info(extra_string = f"DEBUG__", print_current_time = True)
    while condition():
        if time.time() - start_time >= timeout:
            timeouted = True
            break
        time.sleep(time_sleep)
    libprint.print_func_info(extra_string = f"DEBUG__", print_current_time = True)
    if timeouted:
        if timeout_msg is None:
            timeout_msg = "Timeout in while"
        libprint.print_func_info(extra_string = f"DEBUG__", print_current_time = True)
        raise Exception(timeout_msg)

def test_interrupt_initialization():
    libprint.set_global_string("test_interrupt_initialization")
    assert is_port_open(9000)
    assert is_port_open(9001)
    assert is_port_open(9002)
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    def callback(ctx, stop_control):
        time.sleep(15)
        ctx.stop_all()
        stop_control.stop()
    thread = main.start_main_async(callback, log_level = "DEBUG", start = (9000, 9001, 9002), stdout = True)
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
    libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
    def callback(ctx, stop_control):
        libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
        _cond = lambda: not len(ctx.instances) == 1
        while_with_timeout(2, _cond, timeout_msg = "No instance found")
        libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
        assert len(ctx.instances) == 1
        instance = ctx.instances[0]
        timeout_msg = f"instance.is_ready: {instance.is_ready()} server: {ctx.server}"
        libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
        while_with_timeout(60, lambda: not instance.is_ready() or not ctx.server, timeout_msg = timeout_msg)
        libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
        ctx.stop_all()
        libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
        stop_control.stop()
        libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
    thread = main.start_main_async(callback, log_level = "DEBUG", start = ports, server_port = 9003, stdout = True)
    thread.join()
    end_time = time.time()
    libprint.print_func_info(print_current_time = True, extra_string = f"DEBUG__")
    assert (end_time - start_time) <= 60

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
        while_with_timeout(60, _cond1, timeout_msg = "Not ready")
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
    thread = main.start_main_async(callback, log_level = "DEBUG", start = ports, server_port = server_port, stdout = True)
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= 65

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
    main_async_kwargs = {"log_level": "DEBUG", "start": (9000, 9001, 9002), "server_port": server_port, "stdout": True}
    def callback(ctx, stop_control):
        _cond = lambda: not len(ctx.instances) == 1
        while_with_timeout(2, _cond, timeout_msg = "No instance found")
        instance = ctx.instances[0]
        _cond1 = lambda: not instance.is_ready() or not ctx.server
        while_with_timeout(60, _cond1, timeout_msg = "Not ready")
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
    assert (end_time - start_time) <= 70
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
    main_async_kwargs = {"log_level": "INFO", "start": ports, "server_port": server_port, "stdout": True}
    def callback(ctx, stop_control):
        while_with_timeout(2, lambda: not len(ctx.instances) == 2, timeout_msg = "main.get_count_of_instances() != 2")
        instance1 = ctx.instances[0]
        instance2 = ctx.instances[1]
        _cond = lambda: not instance1.is_ready() or not instance2.is_ready() or not ctx.server
        while_with_timeout(60, _cond, timeout_msg = "Not ready")
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
    assert (end_time - start_time) <= 70
