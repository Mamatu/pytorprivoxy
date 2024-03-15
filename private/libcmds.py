from pylibcommons import libprint, libprocess
import logging

import os

log = logging.getLogger(__name__)

def handle_line(line, instances):
    return _handle_line(line, instances)

def _get_commands(instances):
    def convert(a):
        try:
            if a == "all":
                return "all"
            return int(a)
        except ValueError as ve:
            extra_string = f"args can be port number or 'all'. It is {a}"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            raise ve
    _commands = {}
    def _stop(instances, args):
        libprint.print_func_info(logger = log.debug)
        from pylibcommons.libserver import StopExecution
        return StopExecution()
    _commands["stop"] = _stop
    def _read(instances, args):
        libprint.print_func_info(logger = log.debug)
        if len(args) != 0:
            extra_string = f"read: it requires no argument"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            return
        ports = [(i.tor_process.socks_port, i.tor_process.control_port, i.tor_process.listen_port) for i in instances]
        return str(ports)
    _commands["read"] = _read
    def _newnym(instances, args):
        libprint.print_func_info(logger = log.debug)
        control_ports = [convert(a) for a in args]
        is_all = [x for x in control_ports if x == "all"]
        is_all = any(is_all)
        for instance in instances:
            is_this_port = [x for x in control_ports if x == instance.tor_process.control_port]
            is_this_port = any(is_this_port)
            if is_all or is_this_port:
                instance.write_telnet_cmd_authenticate(f"SIGNAL NEWNYM")
    _commands["newnym"] = _newnym
    def _checkip(instances, args):
        libprint.print_func_info(logger = log.debug)
        if len(args) == 0:
            extra_string = f"checkip: it requires at least a one argument"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            return
        privoxy_ports = [convert(a) for a in args]
        is_all = [x for x in privoxy_ports if x == "all"]
        is_all = any(is_all)
        output = None
        for instance in instances:
            is_this_port = [x for x in privoxy_ports if x == instance.privoxy_process.listen_port]
            is_this_port = any(is_this_port)
            if is_all or is_this_port:
                command = f"curl -x \"http://localhost:{instance.privoxy_process.listen_port}\" http://httpbin.org/ip"
                process = libprocess.Process(command, use_temp_file = True, shell = True)
                libprint.print_func_info(prefix = "*", logger = log.info, extra_string = f"Run command {command}")
                process.start()
                process.wait()
                libprint.print_func_info(prefix = "*", logger = log.info, extra_string = f"After command {command}")
                if process.is_stdout():
                    stdout = process.get_stdout()
                    if output is None:
                        output = ""
                    output = output + "\n".join(stdout.readlines())
                else:
                    extra_string = f"checkip: no stdout"
                    libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
        return output
    _commands["checkip"] = _checkip
    return _commands

def _handle_line(line, instances):
    import re
    line = line.rstrip()
    libprint.print_func_info(prefix = "+", logger = log.info, extra_string = f"line: {line}")
    command = re.split('\s+', line)
    if len(command) == 0:
        libprint.print_func_info(prefix = "*", logger = log.error, extra_string = f"line does not contain any command")
        return
    handle_cmds = _get_commands(instances)
    args = []
    if len(command) > 1:
        args = command[1:]
    if command[0] in handle_cmds.keys():
        libprint.print_func_info(prefix = "*", logger = log.info, extra_string = f"{command[0]} {command[1:]}")
        return handle_cmds[command[0]](instances, command[1:])
    else:
        libprint.print_func_info(prefix = "-", logger = log.error, extra_string = f"Does not found handler for command {command[0]}")
