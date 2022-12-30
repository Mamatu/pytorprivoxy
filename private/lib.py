import psutil
import subprocess
import time
import tempfile
import logging

__enable_logging = False

class _Process:
    def __init__(self, cmd):
        self.is_destroyed_flag = False
        import threading
        self.lock = threading.Lock()
        self.cmd = cmd
        self.process = None
    def was_stopped(self):
        return self.is_destroyed_flag
    def emit_warning_during_destroy(self, ex):
        logging.warning(f"{ex}: please verify if process {self.cmd} was properly closed")
    def start(self):
        self.process = subprocess.Popen(self.cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, universal_newlines = True)
        logging.info(f"Start process {self.process}")
    def stop(self):
        self.is_destroyed_flag = True
        if not hasattr(self, "process"):
            return
        if self.process is None:
            return
        self.process.stdout.close()
        self.process.stderr.close()
        try:
            from private import libterminate
            libterminate.terminate_subprocess(self.process)
            self.process = None
        except psutil.NoSuchProcess as nsp:
            self.emit_warning_during_destroy(nsp)
        except subprocess.TimeoutExpired as te:
            self.emit_warning_during_destroy(te)
        logging.info(f"Stop process {self.process}")
    def wait(self):
        if self.process:
            self.process.wait()

class _TorProcess(_Process):
    class Stopped(Exception):
        pass
    class LineError(Exception):
        pass
    def __make_config(self, socks_port, control_port, listen_port, data_directory_path):
        from private import libpass
        config = tempfile.NamedTemporaryFile(mode = "w")
        config.write(f"SocksPort {socks_port}\n")
        config.write(f"ControlPort {control_port}\n")
        config.write(f"DataDirectory {data_directory_path}\n")
        #config.write(f"HashedControlPassword {libpass.get_hashed_password()}\n")
        config.flush()
        return config
    def __init__(self, socks_port, control_port, listen_port):
        self.wait_for_initialization = self._instance_wait_for_initialization
        self.was_initialized = False
        self.data_directory = tempfile.TemporaryDirectory()
        self.config = self.__make_config(socks_port, control_port, listen_port, self.data_directory.name)
        super().__init__(["tor", "-f", self.config.name])
        self.controller = None
        self.socks_port = socks_port
        self.control_port = control_port
        self.listen_port = listen_port
        self.detroy_flag = False
        logging.info(f"Instace of tor process: {self.id_ports()}")
    def is_initialized(self):
        if self.was_initialized:
            return True
        is_initialized_str = "Bootstrapped 100% (done): Done"
        try:
            line = self.process.stdout.readline()
            line = line.replace("\n", "")
            logging.debug(f"{self.id_ports()} {line}")
            if "[err]" in line:
                raise _TorProcess.LineError(str(line))
            if is_initialized_str in line:
                logging.info(f"{self.id_ports()} Initialized: {self.socks_port} {self.control_port} {self.listen_port}")
                self.was_initialized = True
                return True
            return False
        except Exception as ex:
            logging.error(f"{self.id_ports()} {ex}")
            if isinstance(ex, _TorProcess.LineError):
                raise ex
            return False
    @staticmethod
    def wait_for_initialization(callback_is_initialized, callback_to_stop, timeout = 300, delay = 0.5):
        duration = 0
        while True:
            if callback_to_stop():
                raise _TorProcess.Stopped()
            try:
                if callback_is_initialized():
                    return True
            except Exception as ex:
                logging.error(str(ex))
                raise _TorProcess.Stopped()
            time.sleep(delay)
            duration = duration + delay
            if duration >= timeout:
                return False
    def _instance_wait_for_initialization(self, timeout = 300, delay = 0.5):
        """
        It is accessible by self.wait_for_initialization
        """
        status =  _TorProcess.wait_for_initialization(lambda: self.is_initialized(), lambda: self.was_stopped(), timeout, delay)
        if status: self.init_controller()
        return status
    def was_stopped(self):
        return self.detroy_flag
    def start(self):
        super().start()
    def stop(self):
        self._stop()
    def init_controller(self):
        try:
            from stem.control import Controller
            self.controller = Controller.from_port(port = self.control_port)
            from private import libpass
            self.controller.authenticate()
            #self.controller.authenticate(password = libpass.get_password())
            #self.controller.authenticate(libpass.get_hashed_password())
            #self.controller.authenticate(libpass.get_hashed_password(remove_prefix = True))
            def event_listener(event, d, events):
                logging.info(f"event: {event}")
            self.controller.add_event_listener(event_listener)
            def status_listener(controller, state, number):
                logging.info(f"status: {controller} {state} {number}")
            self.controller.add_status_listener(status_listener)
            logging.info(f"Init controller {self.controller}")
        except Exception as ex:
            logging.error(f"Exception: {ex} . Stopping of process")
            self._stop()
            raise ex
    def _stop(self):
        self.detroy_flag = True
        super().stop()
        if hasattr(self, "config"):
            self.config.close()
        if hasattr(self, "data_directory"):
            self.data_directory.cleanup()
    def id_ports(self):
        return f"({self.socks_port} {self.control_port} {self.listen_port})"
    def get_info(self, parameter):
        return self.controller.get_info(parameter)

class _PrivoxyProcess(_Process):
    def __make_config(self, socks_port, listen_port):
        config = tempfile.NamedTemporaryFile(mode = "w")
        config.write(f"forward-socks5t / 127.0.0.1:{socks_port} .\n")
        config.write(f"listen-address 127.0.0.1:{listen_port}\n")
        config.write(f"keep-alive-timeout 600\n")
        config.write(f"default-server-timeout 600\n")
        config.write(f"socket-timeout 600\n")
        config.flush()
        return config
    def __init__(self, socks_port, listen_port):
        self.config = self.__make_config(socks_port, listen_port)
        super().__init__(["privoxy", "--no-daemon", self.config.name])
    def stop(self):
        super().stop()
        if hasattr(self, "config"):
            self.config.close()

class _Instance:
    def __init__(self, tor_process, privoxy_process):
        self.tor_process = tor_process
        self.privoxy_process = privoxy_process
    def __eq__(self, other):
        return self.tor_process == other.tor_process and self.privoxy_process == other.tor_process
    def start(self):
        self.tor_process.start()
        self.privoxy_process.start()
    def stop(self):
        self.tor_process.stop()
        self.privoxy_process.stop()
    def wait_for_initialization(self, timeout = 60, delay = 0.5):
        try:
            return self.tor_process.wait_for_initialization(timeout, delay)
        except _TorProcess.Stopped:
            return False
    def join(self):
        self.privoxy_process.wait()
        self.tor_process.wait()

def _is_port_used(port : int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
        return s.connect_ex(('localhost', port)) == 0

def _make_tor_privoxy_none_block(socks_port, control_port, listen_port):
    privoxy_process = _PrivoxyProcess(socks_port = socks_port, listen_port = listen_port)
    tor_process = _TorProcess(socks_port = socks_port, control_port = control_port, listen_port = listen_port)
    instance = _Instance(tor_process = tor_process, privoxy_process = privoxy_process)
    return instance
