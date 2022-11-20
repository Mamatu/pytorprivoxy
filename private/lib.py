import psutil
import subprocess
import time
import tempfile

import logging

_control_hash_password = "16:5E5D86C529E68C6460807EE16DC0299149D802594B7FA6DB49546552FE"
__enable_logging = False

def set_control_hash_password(control_hash_password):
    global _control_hash_password
    _control_hash_password = control_hash_password

class _Process:
    def __init__(self, cmd):
        import threading
        self.lock = threading.Lock()
        self.process = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, universal_newlines=True)
    def call_safe(self, callback):
        try:
            self.lock.acquire()
            return callback()
        finally:
            self.lock.release()
    def kill(self, wait_for_end = True):
        if not hasattr(self, "process"):
            return
        if self.process is None:
            return
        self.process.stdout.close()
        self.process.stderr.close()
        parent = psutil.Process(self.process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.terminate()
        self.process.terminate()
        if wait_for_end:
            self.process.wait()
        self.process = None
    def __del__(self):
        self.kill()
    def wait(self):
        if self.process:
            self.process.wait()

class _TorProcess(_Process):
    class StopInitialization(Exception):
        pass
    def __make_config(self, socks_port, control_port, listen_port, data_directory_path):
        global _control_hash_password
        config = tempfile.NamedTemporaryFile(mode = "w")
        config.write(f"SocksPort {socks_port}\n")
        config.write(f"ControlPort {control_port}\n")
        config.write(f"DataDirectory {data_directory_path}\n")
        config.write(f"HashedControlPassword {_control_hash_password}\n")
        config.flush()
        return config
    def __init__(self, socks_port, control_port, listen_port):
        self.data_directory = tempfile.TemporaryDirectory()
        self.config = self.__make_config(socks_port, control_port, listen_port, self.data_directory.name)
        super().__init__(["tor", "-f", self.config.name])
        self.socks_port = socks_port
        self.control_port = control_port
        self.listen_port = listen_port
        self.stop_initialization = False
    def is_initialized(self):
        is_initialized_str = "Bootstrapped 100% (done): Done"
        try:
            line = self.process.stdout.readline()
            print(line)
            if is_initialized_str in line:
                logging.info("Initialized: {self.socks_port} {self.control_port} {self.listen_port}")
                return True
            return False
        except Exception as ex:
            print(ex)
            return False
    def wait_for_initialization(self, timeout = 60, timestep = 0.5):
        duration = 0
        while True:
            if self.stop_initialization:
                raise _TorProcess.StopInitialization()
            if self.is_initialized():
                return True
            time.sleep(timestep)
            duration = duration + timestep
            if duration >= timeout:
                return False
    def kill(self):
        self.stop_initialization = True
        super().kill(wait_for_end = False)
        if hasattr(self, "config"):
            self.config.close()
        if hasattr(self, "data_directory"):
            self.data_directory.cleanup()
    def __del__(self):
        self.kill()
        super().__del__()

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
    def kill(self):
        super().kill()
        if hasattr(self, "config"):
            self.config.close()
    def __del__(self):
        self.kill()
        super().__del__()

class _Instance:
    def __init__(self, tor_process, privoxy_process):
        self.tor_process = tor_process
        self.privoxy_process = privoxy_process
    def __eq__(self, other):
        return self.tor_process == other.tor_process and self.privoxy_process == other.tor_process
    def kill(self):
        self.privoxy_process.kill()
        self.tor_process.kill()
    def wait_for_initialization(self, timeout = 60, timestep = 0.5):
        try:
            return self.tor_process.wait_for_initialization(timeout, timestep)
        except _TorProcess.StopInitialization:
            print("false")
            return False
    def wait_for_processes_kill(self):
        self.tor_process.wait()
        self.privoxy_process.wait()

def _is_port_used(port : int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
        return s.connect_ex(('localhost', port)) == 0

def _run_tor_privoxy_none_block(socks_port, control_port, listen_port):
    privoxy_process = _PrivoxyProcess(socks_port = socks_port, listen_port = listen_port)
    tor_process = _TorProcess(socks_port = socks_port, control_port = control_port, listen_port = listen_port)
    instance = _Instance(tor_process = tor_process, privoxy_process = privoxy_process)
    return instance
