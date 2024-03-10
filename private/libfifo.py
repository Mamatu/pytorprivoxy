from pylibcommons import libprint
import logging

log = logging.getLogger("pytorprivoxy")

def start(fifo_path, instances):
    import threading
    thread = threading.Thread(target = _thread_func, args = [fifo_path, instances])
    thread.setDaemon(True)
    thread.start()
    return thread

class _StopExecution:
    pass

def _get_commands(fifo_path, instances):
    _commands = {}
    def _stop(fifo_path, instances, args):
        return _StopExecution()
    _commands["stop"] = _stop
    def _read(fifo_path, instances, args):
        if len(args) != 1 or not isinstance(args[0], str):
            extra_string = f"read: args does not contain path to fifo"
            libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
            return
        ports = [(i.tor_process.socks_port, i.tor_process.control_port, i.tor_process.listen_port) for i in instances]
        with open(args[0], "w") as file:
            file.write(str(ports))
    _commands["read"] = _read
    def _newnym(fifo_path, instances, args):
        def convert(a):
            try:
                if a == "all":
                    return "all"
                return int(a)
            except ValueError as ve:
                extra_string = f"newnym: args can be port number or 'all'. It is {a}"
                libprint.print_func_info(prefix = "*", logger = log.error, extra_string = extra_string)
                raise ve
        control_ports = [convert(a) for a in args]
        is_all = [x for x in control_ports if x == "all"]
        is_all = any(is_all)
        for instance in instances:
            is_this_port = [x for x in control_ports if x == instance.tor_process.control_port]
            is_this_port = any(is_this_port)
            if is_all or is_this_port:
                instance.write_telnet_cmd_authenticate(f"SIGNAL NEWNYM")
    _commands["newnym"] = _newnym
    return _commands

def _handle_line(line, fifo_path, instances):
    import re
    line = line.rstrip()
    libprint.print_func_info(prefix = "*", logger = log.info, extra_string = f"read named fifo line: {line}")
    command = re.split('\s+', line)
    if len(command) == 0:
        libprint.print_func_info(prefix = "*", logger = log.error, extra_string = f"line does not contain any command")
        return
    handle_cmds = _get_commands(fifo_path, instances)
    args = []
    if len(command) > 1:
        args = command[1:]
    if command[0] in handle_cmds.keys():
        return handle_cmds[command[0]](fifo_path, instances, command[1:])
    else:
        libprint.print_func_info(prefix = "*", logger = log.error, extra_string = f"Does not found handler for command {command[0]}")

def _thread_func(fifo_path, instances):
    import os
    os.mkfifo(fifo_path)
    while True:
        with open(fifo_path, "r") as file:
            line = file.readline()
            output = _handle_line(line, fifo_path, instances)
            if isinstance(output, _StopExecution):
                return
