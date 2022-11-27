from private import lib as private
from threading import Thread
import logging

def start(socks_port, control_port, listen_port, callback_before_wait = None, wait_for_initialization = True):
    instance = private._make_tor_privoxy_none_block(socks_port, control_port, listen_port)
    if callback_before_wait:
        callback_before_wait(instance)
    if wait_for_initialization:
        try:
            instance.wait_for_initialization()
        except private._TorProcess.Stopped:
            logging.info("Interrupted")
    return instance

def start_multiple(ports : list, callback_before_wait = None, wait_for_initialization = True):
    instances = [private._make_tor_privoxy_none_block(*pt) for pt in ports]
    if callback_before_wait:
        for i in instances:
            callback_before_wait(i)
    if wait_for_initialization:
        def callback_is_initialized():
            threads = [Thread(target = lambda i: i.tor_process.is_initialized(), args = [i]) for i in instances]
            for t in threads:
                t.start()
            is_initialized = [t.join() for t in threads]
            return all(init is True for init in is_initialized)
        def callback_to_stop():
            return all(i.tor_process.was_destroyed() for i in instances)
        try:
            private._TorProcess.wait_for_initialization(callback_is_initialized = callback_is_initialized, callback_to_stop = callback_to_stop)
        except private._TorProcess.Stopped:
            logging.info("Interrupted")
    return instances

def stop(instance):
    if isinstance(instance, list):
        for i in instance:
            stop(i)
    instance.destroy()
