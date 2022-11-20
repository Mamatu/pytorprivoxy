from private import lib as private

def start(socks_port, control_port, listen_port, wait_for_initialization = True):
    instance = private._run_tor_privoxy_none_block(socks_port, control_port, listen_port)
    if wait_for_initialization:
        instance.wait_for_initialization()
    return instance

def start_multiple(ports : list):
    tor_instances = [_run_tor_privoxy_none_block(*ports_tuple) for ports_tuple in ports]
    fds = [instance[0][1] for instance in tor_instances]
    fds = {fd: False for fd in fds}
    wait_for(fds.keys(), _is_tor_initialized)
    for k in fds.keys():
        k.close()
    return tor_instances

def stop(instance):
    if isinstance(instance, list):
        for i in instance:
            stop(i)
    instance.kill()
