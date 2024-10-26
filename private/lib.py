import psutil
import subprocess

import tempfile
import threading
import time

import logging
log = logging.getLogger("pytorprivoxy")

from pylibcommons import libprint
from pylibcommons import libprocess

import concurrent.futures as concurrent

from stem import Signal
from private import libcontroller

class _Process:
    log = log.getChild(__name__)
    def __init__(self):
        self.is_destroyed_flag = False
        self.lock = threading.Lock()
        self.process = None
        self.cmd = ""
    def was_stopped(self):
        return self.is_destroyed_flag
    def emit_warning_during_destroy(self, ex):
        log.warning(f"{ex}: please verify if process {self.cmd} was properly closed")
    def start(self, cmd):
        self.process = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, universal_newlines = True)
        log.info(f"Start process {self.process}")
    def stop(self):
        self.is_destroyed_flag = True
        if not hasattr(self, "process"):
            return
        if self.process is None:
            return
        with self.lock:
            self.process.stdout.close()
            self.process.stderr.close()
        try:
            from private import libterminate
            libterminate.terminate_subprocess(self.process)
            log.info(f"Stop process {self.process}")
            self.process = None
        except psutil.NoSuchProcess as nsp:
            self.emit_warning_during_destroy(nsp)
        except subprocess.TimeoutExpired as te:
            self.emit_warning_during_destroy(te)
    def callback_safe(self, callback):
        try:
            with self.lock:
                return callback()
        except Exception as ex:
            raise ex
    def wait(self):
        if self.process:
            self.process.wait()

class _TorProcess(_Process):
    class Stopped(Exception):
        pass
    class LineError(Exception):
        pass
    def __make_config(self, socks_port, control_port, listen_port, data_directory_path):
        libprint.print_func_info(prefix = "+", logger = log.debug)
        config = tempfile.NamedTemporaryFile(mode = "w")
        config.write(f"SocksPort {socks_port}\n")
        config.write(f"ControlPort {control_port}\n")
        config.write(f"DataDirectory {data_directory_path}\n")
        #config.write(f"HashedControlPassword {libpass.get_hashed_password()}\n")
        config.flush()
        libprint.print_func_info(prefix = "-", logger = log.debug)
        return config
    def __init__(self, socks_port, control_port, listen_port):
        libprint.print_func_info(prefix = "+", logger = log.debug)
        self.wait_for_initialization = self._instance_wait_for_initialization
        self.was_initialized = False
        self.data_directory = tempfile.TemporaryDirectory()
        self.config = None
        self.controller = None
        self.socks_port = socks_port
        self.control_port = control_port
        self.listen_port = listen_port
        self.stop_flag = False
        log.info(f"Instace of tor process: {self.id_ports()}")
        libprint.print_func_info(prefix = "-", logger = log.debug)
        super().__init__()
    def is_initialized(self):
        libprint.print_func_info(prefix = "+", logger = log.debug)
        try:
            if self.was_initialized:
                return True
            is_initialized_str = "Bootstrapped 100% (done): Done"
            def run_safe():
                nonlocal self
                line = self.process.stdout.readline()
                line = line.replace("\n", "")
                log.info(f"{self.id_ports()} {line}")
                if "[err]" in line:
                    raise _TorProcess.LineError(str(line))
                if is_initialized_str in line:
                    log.info(f"{self.id_ports()} Initialized: {self.socks_port} {self.control_port} {self.listen_port}")
                    self.was_initialized = True
                    return True
                return False
            return self.callback_safe(run_safe)
        except Exception as ex:
            log.error(f"{self.id_ports()} {ex}")
            raise ex
        finally:
            libprint.print_func_info(prefix = "-", logger = log.debug)
    @staticmethod
    def wait_for_initialization(callback_is_initialized, callback_to_stop, timeout = 300, delay = 0.5):
        libprint.print_func_info(prefix = "+", logger = log.debug)
        try:
            duration = 0
            while True:
                if callback_to_stop():
                    raise _TorProcess.Stopped()
                try:
                    if callback_is_initialized():
                        return True
                except Exception as ex:
                    log.error(str(ex))
                    if isinstance(ex, _TorProcess.LineError):
                        import traceback
                        tb = traceback.format_exc()
                        log.error(tb)
                    raise _TorProcess.Stopped()
                time.sleep(delay)
                duration = duration + delay
                if duration >= timeout:
                    return False
        finally:
            libprint.print_func_info(prefix = "-", logger = log.debug)
    def _instance_wait_for_initialization(self, timeout = 300, delay = 0.5):
        """
        It is accessible by self.wait_for_initialization
        """
        libprint.print_func_info(prefix = "+", logger = log.debug)
        status = _TorProcess.wait_for_initialization(lambda: self.is_initialized(), lambda: self.was_stopped(), timeout, delay)
        if status: self.init_controller()
        libprint.print_func_info(prefix = "-", logger = log.debug)
        return status
    def was_stopped(self):
        return self.stop_flag
    def start(self):
        self.config = self.__make_config(self.socks_port, self.control_port, self.listen_port, self.data_directory.name)
        super().start(["tor", "-f", self.config.name])
    def stop(self):
        self._stop()
        self.stop_flag = True
        self.was_initialized = False
    def get_url(self):
        return f"http://127.0.0.1:{self.listen_port}"
    def init_controller(self):
        try:
            libprint.print_func_info(prefix = "+", logger = log.debug)
            self.controller = libcontroller.create(self.control_port)
            from private import libpass
            #self.controller.authenticate()
            self.controller.authenticate(password = libpass.get_password())
            #self.controller.authenticate(libpass.get_hashed_password())
            #self.controller.authenticate(libpass.get_hashed_password(remove_prefix = True))
            self.controller.signal(Signal.NEWNYM)
            def event_listener(event, d, events, user_data):
                extra_string = f"{user_data} event: {event}"
                libprint.print_func_info(logger = log.debug, extra_string = extra_string)
            self.controller.add_event_listener(event_listener, user_data = self.id_ports())
            def status_listener(controller, state, number, user_data):
                extra_string = f"{user_data} status: {controller} {state} {number}"
                libprint.print_func_info(logger = log.debug, extra_string = extra_string)
            self.controller.add_status_listener(status_listener, user_data = self.id_ports())
            extra_string = f"Init controller {self.controller}"
            libprint.print_func_info(logger = log.debug, extra_string = extra_string)
        except Exception as ex:
            log.error(f"Exception: {ex} . Stopping of process")
            self._stop()
            raise ex
        finally:
            libprint.print_func_info(prefix = "-", logger = log.debug)
    def _stop(self):
        libprint.print_func_info(prefix = "+", logger = log.debug)
        self.stop_flag = True
        super().stop()
        if hasattr(self, "config"):
            self.config.close()
        if hasattr(self, "data_directory"):
            self.data_directory.cleanup()
        libprint.print_func_info(prefix = "-", logger = log.debug)
    def id_ports(self):
        return f"({self.socks_port} {self.control_port} {self.listen_port})"
    def get_info(self, parameter):
        return self.controller.get_info(parameter)

class _PrivoxyProcess(libprocess.Process):
    def __make_config(self, socks_port, listen_port):
        config = tempfile.NamedTemporaryFile(mode = "w")
        config.write(f"forward-socks5t / 127.0.0.1:{socks_port} .\n")
        config.write(f"listen-address 127.0.0.1:{listen_port}\n")
        config.write("keep-alive-timeout 600\n")
        config.write("default-server-timeout 600\n")
        config.write("socket-timeout 600\n")
        config.flush()
        import os
        os.chmod(config.name, 0o777)
        return config
    def __init__(self, socks_port, listen_port):
        self.config = None
        self.socks_port = socks_port
        self.listen_port = listen_port
        libprint.print_func_info(prefix = "+", logger = log.info)
        self.config = self.__make_config(self.socks_port, self.listen_port)
        cmd = f"privoxy --no-daemon {self.config.name}"
        libprint.print_func_info(prefix = "+", logger = log.info, extra_string = f"privoxy cmd: {cmd}")
        super().__init__(cmd = cmd)
    def start(self):
        super().start()
    def stop(self):
        libprint.print_func_info(prefix = "+", logger = log.info)
        super().stop()
        if hasattr(self, "config"):
            self.config.close()
    def wait(self, **kwargs):
        libprint.print_func_info(prefix = "+", logger = log.info)
        super().wait(exception_on_error = True, print_stdout = True, print_stderr = True)
    def get_listen_port(self):
        return self.listen_port

import enum
class InitializationState(enum.Enum):
    OK = 0,
    TIMEOUT = 1,
    STOPPED = 2

class _Instance:
    log = log.getChild(__name__)
    def __init__(self, tor_process, privoxy_process):
        self.ready = False
        self.tor_process = tor_process
        self.privoxy_process = privoxy_process
        self.quit = False
        self.cv = threading.Condition()
        self._executor = None
    def __eq__(self, other):
        return self.tor_process == other.tor_process and self.privoxy_process == other.tor_process
    def start(self, timeout = 60, delay = 0.5):
        self.privoxy_process.start()
        self.tor_process.start()
        return self._run_initialization()
    def stop(self):
        self._stop()
        with self.cv:
            self.quit = True
            self.cv.notify()
    def _stop(self):
        self.ready = False
        self.tor_process.stop()
        self.privoxy_process.stop()
    def _run_initialization(self, timeout = 60, delay = 0.5):
        def thread_func(self, timeout, delay):
            try:
                output = self.tor_process.wait_for_initialization(timeout, delay)
                if output:
                    self.ready = True
                    return InitializationState.OK
                else:
                    return InitializationState.TIMEOUT
            except _TorProcess.Stopped:
                return False
        if self._executor is None:
            self._executor = concurrent.ThreadPoolExecutor()
        return self._executor.submit(thread_func, self, timeout, delay)
    def write_telnet_cmd(self, cmd):
        from private import libtelnet
        libtelnet.write("localhost", self.tor_process.control_port, cmd)
    def get_url(self):
        return self.tor_process.get_url()
    def get_privoxy_listen_port(self):
        return self.privoxy_process.get_listen_port()
    def write_telnet_cmd_authenticate(self, cmd):
        self.write_telnet_cmd(["authenticate", cmd])
    def join(self):
        with self.cv:
            while not self.quit:
                self.cv.wait()
        self._stop()
    def restart(self):
        self._stop()
        self.start()
    def is_ready(self):
        return self.ready

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

def _is_port_used(port : int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def _while_port_used(port : int) -> bool:
    try:
        while_with_timeout(5, lambda: _is_port_used(port))
    except Exception:
        return True
    return False

def is_port_open(port : int) -> bool:
    return not _while_port_used(port)

def _make_tor_privoxy_none_block(socks_port, control_port, listen_port):
    libprint.print_func_info(prefix = "+", logger = log.debug)
    privoxy_process = _PrivoxyProcess(socks_port = socks_port, listen_port = listen_port)
    tor_process = _TorProcess(socks_port = socks_port, control_port = control_port, listen_port = listen_port)
    instance = _Instance(tor_process = tor_process, privoxy_process = privoxy_process)
    libprint.print_func_info(prefix = "-", logger = log.debug)
    return instance
