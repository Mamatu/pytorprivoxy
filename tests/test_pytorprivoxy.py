import main
import time

from pylibcommons import libprint
from private.lib import is_port_open

import logging

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
    libprint.set_global_string("test_interrupt_initialization")
    assert is_port_open(9000)
    assert is_port_open(9001)
    assert is_port_open(9002)
    start_time = time.time()
    import logging
    log = logging.getLogger('pytorprivoxy')
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = (9000, 9001, 9002), stdout = True)
    time.sleep(15)
    main.stop_all()
    stop_control.stop()
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= 60
    time.sleep(5)

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
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = ports, server = 9003, stdout = True)
    time.sleep(1)
    _cond = lambda: not main.get_count_of_instances() == 1
    while_with_timeout(2, _cond, timeout_msg = "No instance found")
    instance = main.get_instance(0)
    timeout_msg = "instance.is_ready: {instance.is_ready()} server: {main.get_server()}"
    while_with_timeout(60, lambda: not instance.is_ready() or not main.get_server(), timeout_msg = timeout_msg)
    main.stop_all()
    stop_control.stop()
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= 60
    time.sleep(5)
    main.clear_server()

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
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = ports, server = server_port, stdout = True)
    _cond = lambda: not main.get_count_of_instances() == 1
    while_with_timeout(2, _cond, timeout_msg = "No instance found")
    instance = main.get_instance(0)
    _cond1 = lambda: not instance.is_ready() or not main.get_server()
    while_with_timeout(60, _cond1, timeout_msg = "Not ready")
    from multiprocessing.connection import Client
    with Client(("localhost", server_port)) as client:
        import json
        client.send("checkip 9002")
        data = client.recv()
        ipaddress = _get_ip_address(data)
        assert ipaddress != None
        client.send("stop")
    main.stop_all()
    stop_control.stop()
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= 65
    time.sleep(5)
    main.clear_server()

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
    main_async_kwargs = {"log_level": "DEBUG", "start": (9000, 9001, 9002), "server": server_port, "stdout": True}
    thread, stop_control = main.start_main_async(**main_async_kwargs)
    while_with_timeout(2, lambda: not main.get_count_of_instances() == 1, timeout_msg = "No instance found")
    instance = main.get_instance(0)
    while_with_timeout(60, lambda: not instance.is_ready() or not main.get_server(), timeout_msg = "Not ready")
    from multiprocessing.connection import Client
    libprint.print_func_info(logger = log.info, prefix = "+")
    with Client(("localhost", server_port)) as client:
        #import json
        client.send("checkip 9002")
        data = client.recv()
        ipaddress1 = _get_ip_address(data)
        client.send("newnym 9001")
        data = client.recv()
        client.send("checkip 9002")
        data = client.recv()
        ipaddress2 = _get_ip_address(data)
        #if ipaddress1 == ipaddress2:
        #    ipaddress1 = _get_ip_address(data)
        #    client.send("newnym 9001")
        #    ipaddress2 = _get_ip_address(data)
        client.send("stop")
        main.stop_all()
        stop_control.stop()
        thread.join()
        end_time = time.time()
        #assert ipaddress1 != ipaddress2
        assert (end_time - start_time) <= 65
    libprint.print_func_info(logger = log.info, prefix = "-")
    time.sleep(5)
    main.clear_server()

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
    main_async_kwargs = {"log_level": "INFO", "start": ports, "server": server_port, "stdout": True}
    thread, stop_control = main.start_main_async(**main_async_kwargs)
    while_with_timeout(2, lambda: not main.get_count_of_instances() == 2, timeout_msg = "main.get_count_of_instances() != 2")
    instance1 = main.get_instance(0)
    instance2 = main.get_instance(1)
    _cond = lambda: not instance1.is_ready() or not instance2.is_ready() or not main.get_server()
    while_with_timeout(60, _cond, timeout_msg = "Not ready")
    from multiprocessing.connection import Client
    with Client(("localhost", server_port)) as client:
        #import json
        client.send("checkip 9002")
        data = client.recv()
        ipaddress1 = _get_ip_address(data)
        client.send("newnym 9001")
        data = client.recv()
        time.sleep(10)
        client.send("checkip 9002")
        data = client.recv()
        ipaddress2 = _get_ip_address(data)
        client.send("stop")
        main.stop_all()
        stop_control.stop()
        thread.join()
        end_time = time.time()
        assert ipaddress1 != ipaddress2
        assert (end_time - start_time) <= 70
    time.sleep(5)
    main.clear_server()
