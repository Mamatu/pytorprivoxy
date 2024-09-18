import main
import time

from pylibcommons import libprint

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
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = (9000, 9001, 9002), stdout = True)
    time.sleep(15)
    main.stop_all()
    stop_control.stop()
    thread.join()
    end_time = time.time()
    assert (end_time - start_time) <= 17

def test_initialize():
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = (9000, 9001, 9002), server = 9003, stdout = True)
    time.sleep(1)
    while not main.get_count_of_instances() == 1:
        time.sleep(1)
    instance = main.get_instance(0)
    while not instance.is_ready():
        time.sleep(1)
    main.stop_all()
    stop_control.stop()
    thread.join()
    end_time = time.time()
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
    server_port = 9003
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = (9000, 9001, 9002), server = server_port, stdout = True)
    while_with_timeout(2, lambda: not main.get_count_of_instances() == 1, timeout_msg = "No instance found")
    instance = main.get_instance(0)
    while_with_timeout(60, lambda: not instance.is_ready(), timeout_msg = "Not ready")
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

def test_newnym():
    server_port = 9003
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    main_async_kwargs = {"log_level": "DEBUG", "start": (9000, 9001, 9002), "server": server_port, "stdout": True}
    thread, stop_control = main.start_main_async(**main_async_kwargs)
    while_with_timeout(2, lambda: not main.get_count_of_instances() == 1, timeout_msg = "No instance found")
    instance = main.get_instance(0)
    while_with_timeout(60, lambda: not instance.is_ready(), timeout_msg = "Not ready")
    from multiprocessing.connection import Client
    def client_operation():
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
            client.send("stop")
            main.stop_all()
            stop_control.stop()
            thread.join()
            end_time = time.time()
            assert ipaddress1 != ipaddress2
            assert (end_time - start_time) <= 65
        libprint.print_func_info(logger = log.info, prefix = "-")
    try:
        client_operation()
    except Exception:
        client_operation()

def test_newnym_2_instances():
    server_port = 9006
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    main_async_kwargs = {"log_level": "INFO", "start": [[9000, 9001, 9002], [9003, 9004, 9005]], "server": server_port, "stdout": True}
    thread, stop_control = main.start_main_async(**main_async_kwargs)
    while_with_timeout(2, lambda: not main.get_count_of_instances() == 2, timeout_msg = "main.get_count_of_instances() != 2")
    instance1 = main.get_instance(0)
    instance2 = main.get_instance(1)
    while_with_timeout(60, lambda: not instance1.is_ready() or not instance2.is_ready(), timeout_msg = "Not ready")
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
