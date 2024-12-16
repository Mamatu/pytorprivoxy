from private import lib as private
from private import libcmds
import sys

import logging
log = logging.getLogger('pytorprivoxy')

from pylibcommons import libprint, libkw, libprocess, libprocess

def start(socks_port : int, control_port : int, listen_port : int, **kwargs):
    return start_multiple([(socks_port, control_port, listen_port)], **kwargs)

def start_multiple(ports : list, **kwargs):
    callback_before_wait = libkw.handle_kwargs("callback_before_wait", default_output = None)
    wait_for_initialization = libkw.handle_kwargs("wait_for_initialization", default_output = False)
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
    libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{instances}")
    futures = []
    for i in instances:
        future = i.start(**kwargs)
        futures.append(future)
    if callback_before_wait:
        for i in instances: callback_before_wait(i)
    libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{instances}")
    if wait_for_initialization:
        results = [f.result() for f in futures]
        libprint.print_func_info(prefix = "*", logger = log.info, extra_string = f"results for initialization {results}")
    server = _try_create_server(instances, **kwargs)
    libprint.print_func_info(prefix = "-", logger = log.debug)
    output = {}
    output["instances"] = instances
    if server:
        output["server"] = server
    if not wait_for_initialization:
        output["futures"] = futures
    return output

def stop(instance):
    libprint.print_func_info(logger = log.debug)
    if isinstance(instance, list):
        for i in instance:
            i.stop()
    else:
        stop([instance])

def join(instance):
    libprint.print_func_info(logger = log.debug)
    if isinstance(instance, list):
        for i in instance:
            i.join()
    else:
        join([instance])

def get_pids(instance):
    if isinstance(instance, list):
        pids = []
        for i in instance:
            pids = pids + get_pids(i)
        return pids
    return instance.get_pids()

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
    logging.basicConfig(level = logging.DEBUG)
    expected_levels = {"CRITICAL" : logging.CRITICAL, "ERROR" : logging.ERROR, "WARNING" : logging.WARNING, "INFO" : logging.INFO, "DEBUG" : logging.DEBUG}
    if not log_level in expected_levels.keys():
        raise Exception(f'{log_level} is not supported. Should be {",".join(expected_levels.keys())}')
    else:
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for log in loggers:
            log.setLevel(level = expected_levels[log_level])

def _try_create_server(instances, **kwargs):
    server_port = libkw.handle_kwargs("server_port", default_output = None, **kwargs)
    if server_port is not None:
        from pylibcommons import libserver
        def handler(line, client):
            try:
                libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"line {line}")
                output = libcmds.handle_line(line, instances)
                libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"output {output} for line {line}")
                if isinstance(output, str):
                    client.send(output)
                return output
            except Exception as ex:
                libprint.print_func_info(extra_string = f"{ex}", logger = log.error)
                client.send(str(ex))
        address = ("localhost", server_port)
        libprint.print_func_info(prefix = "+", logger = log.debug)
        server = libserver.run(handler, address)
        libprint.print_func_info(prefix = "-", extra_string = f"Multiprocess server {server} run on {address}", logger = log.info)
        return server
    return None

stdout_handler = None
def enable_stdout():
    global stdout_handler
    if stdout_handler is None:
        handler = logging.StreamHandler(sys.stdout)
        log.addHandler(handler)
        stdout_handler = handler

def manage_multiple(ports : list, **kwargs):
    rpf = kwargs["runnig_pool_factor"]
    if "success_factor" in kwargs:
        success_factor = kwargs["success_factor"]
    ports_len = len(ports)
    ports_len_to_run = ports_len * rpf
    run_ports = ports[:ports_len_to_run]
    start_multiple(run_ports, success_factor = success_factor)
