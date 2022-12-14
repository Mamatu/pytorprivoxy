from private import lib as private
import logging

import concurrent.futures as concurrent

def start(socks_port, control_port, listen_port, callback_before_wait = None, wait_for_initialization = True, **kwargs):
    instance = private._make_tor_privoxy_none_block(socks_port, control_port, listen_port)
    instance.start()
    if callback_before_wait:
        callback_before_wait(instance)
    if wait_for_initialization:
        try:
            if not instance.wait_for_initialization(timeout = kwargs['timeout']):
                raise TimeoutError()
        except private._TorProcess.Stopped:
            logging.info("Interrupted")
    return instance

def start_multiple(ports : list, callback_before_wait = None, wait_for_initialization = True, **kwargs):
    instances = [private._make_tor_privoxy_none_block(*pt) for pt in ports]
    for i in instances:
        i.start()
    success_factor = 1
    if "success_factor" in kwargs:
        success_factor = kwargs["success_factor"]
    if callback_before_wait:
        for i in instances:
            callback_before_wait(i)
    if wait_for_initialization:
        def callback_is_initialized():
            with concurrent.ThreadPoolExecutor() as executor:
                def is_initialized_async(i):
                    return i.tor_process.is_initialized()
                futures = [executor.submit(is_initialized_async, i) for i in instances]
                is_initialized = [f.result() for f in futures]
                true_count = len([1 for i in is_initialized if i is True])
                factor = float(true_count) / float(len(is_initialized))
                return factor >= success_factor
        def callback_to_stop():
            return all(i.tor_process.was_stopped() for i in instances)
        try:
            if not private._TorProcess.wait_for_initialization(callback_is_initialized = callback_is_initialized, callback_to_stop = callback_to_stop, timeout = kwargs['timeout']):
                raise TimeoutError()
        except private._TorProcess.Stopped:
            logging.info("Interrupted")
    return instances

def stop(instance):
    if isinstance(instance, list):
        for i in instance:
            stop(i)

def manage_multiple(ports : list, **kwargs):
    rpf = kwargs["runnig_pool_factor"]
    success_facctor = 1.
    if "success_factor" in kwargs:
        success_factor = kwargs["success_factor"]
    ports_len = len(ports)
    ports_len_to_run = ports * rpf
    run_ports = ports[:ports_len_to_run]
    start_multiple(run_ports, success_factor = success_factor)
