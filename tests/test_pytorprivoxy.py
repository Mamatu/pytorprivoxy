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
    assert (end_time - start_time) <= 25

def test_get_ip():
    server_port = 9003
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    thread, stop_control = main.start_main_async(log_level = "DEBUG", start = (9000, 9001, 9002), server = server_port, stdout = True)
    libprint.print_func_info(logger = log.info)
    time.sleep(1)
    while_with_timeout(2, lambda: not main.get_count_of_instances() == 1, timeout_msg = "No instance found")
    libprint.print_func_info(logger = log.info)
    instance = main.get_instance(0)
    while_with_timeout(25, lambda: not instance.is_ready(), timeout_msg = "Not ready")
    libprint.print_func_info(logger = log.info)
    from multiprocessing.connection import Client
    client = Client(("localhost", server_port))
    client.send("checkip 9002")
    import json
    libprint.print_func_info(logger = log.info)
    data = client.recv()
    libprint.print_func_info(logger = log.info)
    try:
        data = json.loads(data)
        import ipaddress
        _ipaddress = ipaddress.ip_address(data['origin'])
        print(_ipaddress)
    except Exception as e:
        pass
    libprint.print_func_info(logger = log.info)
    client.send("stop")
    libprint.print_func_info(logger = log.info)
    main.stop_all()
    stop_control.stop()
    thread.join()
    end_time = time.time()
    libprint.print_func_info(logger = log.info)
    assert (end_time - start_time) <= 25
