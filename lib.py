from private import lib as private
import concurrent.futures as concurrent

import logging
import sys
log = logging.getLogger("pytorprivoxy")

from pylibcommons import libprint

def start(socks_port : int, control_port : int, listen_port : int, callback_before_wait = None, wait_for_initialization = True, **kwargs):
    libprint.print_func_info(prefix = "+", logger = log.debug)
    instance = private._make_tor_privoxy_none_block(socks_port, control_port, listen_port)
    instance.start()
    if callback_before_wait:
        callback_before_wait(instance)
    if wait_for_initialization:
        try:
            if not instance.wait_for_initialization(timeout = kwargs['timeout']):
                raise TimeoutError()
        except private._TorProcess.Stopped:
            log.info("Interrupted")
            instance.stop()
    libprint.print_func_info(prefix = "-", logger = log.debug)
    return instance

def start_multiple(ports : list, callback_before_wait = None, wait_for_initialization = True, **kwargs):
    libprint.print_func_info(prefix = "+", logger = log.debug)
    def invalid_ports(ports):
        raise Exception(f"Ports must be list of int tuple or int list (of 3 size): it is: {ports}")
    def check_ports(ports):
        for p in ports:
            if isinstance(p, tuple) or isinstance(p, list):
                if len(p) == 3:
                    for i in p:
                        if not isinstance(i, int):
                            invalid_ports(ports)
                else:
                    invalid_ports(ports)
            else:
                invalid_ports(ports)
    check_ports(ports)
    instances = [private._make_tor_privoxy_none_block(*pt) for pt in ports]
    for i in instances: i.start()
    success_factor = 1
    if "success_factor" in kwargs:
        success_factor = kwargs["success_factor"]
    if callback_before_wait:
        for i in instances: callback_before_wait(i)
    libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{instances}")
    if wait_for_initialization:
        def callback_is_initialized():
            with concurrent.ThreadPoolExecutor() as executor:
                def is_initialized_async(i):
                    is_init = i.tor_process.is_initialized()
                    libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{i}.tor_process.is_initialized() = {is_init}")
                    return is_init
                libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{instances}")
                futures = [executor.submit(is_initialized_async, i) for i in instances]
                is_initialized = [f.result() for f in futures]
                true_count = len([1 for i in is_initialized if i is True])
                factor = float(true_count) / float(len(is_initialized))
                return factor >= success_factor
        def callback_to_stop():
            return all([i.tor_process.was_stopped() for i in instances])
        try:
            libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{instances}")
            if not private._TorProcess.wait_for_initialization(callback_is_initialized = callback_is_initialized, callback_to_stop = callback_to_stop, timeout = kwargs['timeout']):
                raise TimeoutError()
            else:
                for i in instances: i.tor_process.init_controller()
        except private._TorProcess.Stopped:
            for i in instances: i.stop()
            log.info("Interrupted")
        except Exception as ex:
            log.error(f"{ex}")
    libprint.print_func_info(prefix = "-", logger = log.debug)
    return instances

def stop(instance):
    if isinstance(instance, list):
        for i in instance: i.stop()
    else:
        stop([instance])

def control(instance, cmd):
    instance.write_telnet_cmd(cmd)

def newnym(instance):
    if isinstance(instance, list):
        for i in instance: newnym(i)
    control(instance, "SIGNAL NEWNYM")

def get_url(instance):
    if isinstance(instance, list):
        return [get_url(i) for i in instance]
    return instance.get_url()

def set_logging_level(log_level):
    expected_levels = {"CRITICAL" : logging.CRITICAL, "ERROR" : logging.ERROR, "WARNING" : logging.WARNING, "INFO" : logging.INFO, "DEBUG" : logging.DEBUG}
    if not log_level in expected_levels.keys():
        raise Exception(f'{args.log_level} is not supported. Should be {",".join(expected_levels.keys())}')
    else:
        log.setLevel(level = expected_levels[log_level])

def enable_stdout():
    handler = logging.StreamHandler(sys.stdout)
    log.addHandler(handler)

def manage_multiple(ports : list, **kwargs):
    rpf = kwargs["runnig_pool_factor"]
    success_facctor = 1.
    if "success_factor" in kwargs:
        success_factor = kwargs["success_factor"]
    ports_len = len(ports)
    ports_len_to_run = ports * rpf
    run_ports = ports[:ports_len_to_run]
    start_multiple(run_ports, success_factor = success_factor)
