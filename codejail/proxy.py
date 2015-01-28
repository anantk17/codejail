"""A proxy subprocess-making process for CodeJail."""

import ast
import os.path
import subprocess
import sys

from .subproc import run_subprocess

# We use .readline to get data from the pipes between the processes, so we need
# to ensure that a newline does not appear in the data.  We also need a way to
# communicate a few values, and unpack them.  Lastly, we need to be sure we can
# handle binary data.  Serializing with repr() and deserializing the literals
# that result give us all the properties we need.
serialize = repr
deserialize = ast.literal_eval

# There is one global proxy process.
PROXY_PROCESS = None

def run_subprocess_through_proxy(*args, **kwargs):
    """
    Works just like :ref:`run_subprocess`, but through the proxy process.
    """
    global PROXY_PROCESS
    if PROXY_PROCESS is None:
        # Start the proxy by invoking proxy_main.py in our root directory.
        root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        proxy_main_py = os.path.join(root, "proxy_main.py")

        # Run proxy_main.py with the same Python that is running us. "-u" makes
        # the stdin and stdout unbuffered.
        PROXY_PROCESS = subprocess.Popen(
            [sys.executable, '-u', proxy_main_py],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )

    stdin = serialize((args, kwargs))
    PROXY_PROCESS.stdin.write(stdin+"\n")

    stdout = PROXY_PROCESS.stdout.readline()
    retval = deserialize(stdout.rstrip())
    return retval

# Set this to True to see what the proxy process is doing.
LOG_PROXY = False


def proxy_main():
    """
    The main program for the proxy process.

    It does this:

        * Reads a line from stdin with the repr of a tuple: (args, kwargs)
        * Calls :ref:`run_subprocess` with *args, **kwargs
        * Writes one line to stdout: the repr of the return value from
          `run_subprocess`: (pid, status, stdout, stderr).

    The process ends when its stdin is closed.

    """
    if LOG_PROXY:
        flog = open("/tmp/proxy.log", "a")
    def log(s):
        if LOG_PROXY:
            flog.write(s)
            flog.write("\n")
            flog.flush()

    log("Starting")
    try:
        while True:
            stdin = sys.stdin.readline()
            log("stdin: %r" % stdin)
            if not stdin:
                break
            args, kwargs = deserialize(stdin.rstrip())
            pid, status, stdout, stderr = run_subprocess(*args, **kwargs)
            log("pid=%r\nstatus=%r\nstdout=%r\nstderr=%r" % (pid, status, stdout, stderr))
            stdout = serialize((pid, status, stdout, stderr))
            sys.stdout.write(stdout+"\n")
    except Exception:
        if LOG_PROXY:
            import traceback
            traceback.print_exc(999, flog)

    log("Exiting")
    if LOG_PROXY:
        flog.flush()
