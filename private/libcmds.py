from pylibcommons import libprint, libprocess

import logging
log = logging.getLogger('pytorprivoxy')

import time
import json
import re

def handle_line(line, instances):
    libprint.print_func_info(prefix = "+", logger = log.debug, extra_string = f"line: {line}")
    return _handle_line(line, instances)

def get_instances(ports, instances, callback):
    is_all = [x for x in ports if x == "all"]
    is_all = any(is_all)
    output = []
    for instance in instances:
        is_this_port = [x for x in ports if x == callback(instance)]
        is_this_port = any(is_this_port)
        if is_all or is_this_port:
            output.append(instance)
    return output

def _get_commands(instances):
    libprint.print_func_info(logger = log.debug)
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
            extra_string = "read: it requires no argument"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            return
        ports = [(i.tor_process.socks_port, i.tor_process.control_port, i.tor_process.listen_port) for i in instances]
        return str(ports)
    _commands["read"] = _read
    def _newnym(instances, args):
        libprint.print_func_info(logger = log.debug)
        control_ports = [convert(a) for a in args]
        instances = get_instances(control_ports, instances, lambda x: x.tor_process.control_port)
        for instance in instances:
            instance.write_telnet_cmd_authenticate("SIGNAL NEWNYM")
        time.sleep(8)
        return json.dumps({"status" : "ok"})
    _commands["newnym"] = _newnym
    def _checkip(instances, args):
        libprint.print_func_info(logger = log.debug)
        if len(args) == 0:
            extra_string = "checkip: it requires at least a one argument"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            return
        privoxy_ports = [convert(a) for a in args]
        instances = get_instances(privoxy_ports, instances, lambda x: x.privoxy_process.listen_port)
        outputs = {}
        for instance in instances:
            command = f"curl -f -x \"http://localhost:{instance.privoxy_process.listen_port}\" https://check.torproject.org/"
            process = libprocess.Process(command, use_temp_file = True, shell = True)
            libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"Run command {command}")
            process.start()
            return_code = 0
            def callback_on_error_func(error, stdout, stderr):
                libprint.print_func_info(prefix = "*", logger = log.error, extra_string = f"checkip: error {error} stdout {stdout} stderr {stderr}")
                return error
            return_code = process.wait(callback_on_error = callback_on_error_func, print_stdout = True, print_stderr = True)
            if return_code is None:
                return_code = 0
            libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"After command {command}")
            if process.is_stdout():
                stdout = process.get_stdout()
                readlines = stdout.readlines()
                body = "\n".join(readlines)
                match = re.search(r"Your IP address appears to be:  <strong>([0-9]*.[0-9]*.[0-9]*.[0-9]*)</strong>", body)
                ip = match.group(1)
                match_is_tor = re.search(r"Congratulations. This browser is configured to use Tor.", body)
                is_tor = False
                is_not_tor = True
                if match_is_tor is not None:
                    is_tor = True
                match_is_not_tor = re.search(r"Sorry. You are not using Tor", body)
                if match_is_not_tor is None:
                    is_not_tor = False
                IS_TOR = False
                if is_tor and not is_not_tor:
                    IS_TOR = True
                elif not is_tor and is_not_tor:
                    IS_TOR = False
                else:
                    IS_TOR = None
                    libprint.print_func_info(prefix = "*", logger = log.error, extra_string = f"checkip: unexpected result of is_tor and is_not_tor {is_tor} {is_not_tor} {match_is_tor} {match_is_not_tor}")
                outputs[instance.privoxy_process.listen_port] = {"address" : ip, "is_tor" : IS_TOR, "return_code" : return_code}
            else:
                extra_string = "checkip: no stdout"
                libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
        libprint.print_func_info(logger = log.debug, extra_string = f"checkip: outputs {outputs}")
        return json.dumps(outputs)
    _commands["checkip"] = _checkip
    def _restart(instances, args):
        libprint.print_func_info(logger = log.debug)
        if len(args) == 0:
            extra_string = "checkip: it requires at least a one argument"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            return
        tor_ports = [convert(a) for a in args]
        instances = get_instances(tor_ports, instances, lambda x: x.tor_process.socks_port)
        for instance in instances:
            instance.restart()
    _commands["restart"] = _restart
    return _commands

def _handle_line(line, instances):
    import re
    line = line.rstrip()
    libprint.print_func_info(prefix = "+", logger = log.debug, extra_string = f"line: {line}")
    command = re.split('\\s+', line)
    if len(command) == 0:
        libprint.print_func_info(prefix = "*", logger = log.error, extra_string = "line does not contain any command")
        return
    handle_cmds = _get_commands(instances)
    if command[0] in handle_cmds.keys():
        libprint.print_func_info(prefix = "*", logger = log.debug, extra_string = f"{command[0]} {command[1:]}")
        return handle_cmds[command[0]](instances, command[1:])
    else:
        libprint.print_func_info(prefix = "-", logger = log.error, extra_string = f"Does not found handler for command {command[0]}")
