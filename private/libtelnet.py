from pylibcommons import libprint
import logging
import telnetlib

log = logging.getLogger("pytorprivoxy")

def write(address, port, cmds):
    if isinstance(cmds, str):
        cmds = [cmds]
    libprint.print_func_info(prefix = "+", logger = log.debug, extra_string = f"cmds: {cmds}")
    with telnetlib.Telnet(host = address, port = port) as tn:
        write = lambda cmds: tn.write(cmds.encode("ascii"))
        if isinstance(cmds, list) or isinstance(cmds, tuple):
            for c in cmds: write(f"{c}\n")
        else:
            log.info(f"telnet {tn} write: {cmds}")
            write(cmds)
    libprint.print_func_info(prefix = "-", logger = log.debug, extra_string = f"cmds: {cmds}")
