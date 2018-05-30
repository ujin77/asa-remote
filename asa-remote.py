#!/usr/bin/python
# -*- coding: utf-8
#

import paramiko
import os
import sys
import time
import argparse
import re

PROG = os.path.basename(sys.argv[0]).rstrip('.py')
PROG_DESC = 'Cisco ASA shell client'

enable_output = False


def _out(str_text):
    if enable_output:
        sys.stdout.write(str_text)
        sys.stdout.flush()


def _err(str_text):
    sys.stderr.write(str_text)
    sys.stderr.flush()


class ASAClient(object):

    client = paramiko.SSHClient()
    data_timeout = 5
    answer_timeout = 3
    connected = False
    std_in = None
    std_out = None
    shell = None

    def __init__(self, hostname, username, password):
        super(ASAClient, self).__init__()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.password = password
        try:
            self.client.connect(hostname=hostname, username=username, password=password,
                                look_for_keys=False, timeout=self.data_timeout)
            self.shell = self.client.invoke_shell()
            self.shell.settimeout(3)
        except Exception as e:
            _err(str(e))
            return
        self.std_in = self.shell.makefile('wb')
        self.std_out = self.shell.makefile('rb')
        if not self._wait_answer('(\>|#)\s', first_run=True):
            self.close()
        else:
            self.connected = True

    def _wait_data_from_shell(self):
        timeout = self.data_timeout * 10
        while timeout and not self.shell.recv_ready():
            timeout -= 1
            time.sleep(.1)
        if timeout:
            return True
        _err('Data timeout: %s sec' % self.data_timeout)
        return False

    def _is_answer(self, pattern):
        self._wait_data_from_shell()
        if self.shell.recv_ready():
            answer = self.shell.recv(1024)
            _out(answer)
            if re.search(pattern, answer):
                return True
        return False

    def _wait_answer(self, pattern, first_run=False):
        if self.connected or first_run:
            timeout = self.answer_timeout * 10
            while timeout and not self._is_answer(pattern):
                timeout -= 1
                time.sleep(.1)
            if timeout:
                return True
            _err('Answer timeout: %s sec' % self.answer_timeout)
        return False

    def _write(self, buf, new_line=True):
        if self.connected:
            self.std_in.write(buf)
            if new_line:
                self.std_in.write("\n")

    def _read_shell(self):
        if self.connected:
            self._wait_data_from_shell()
            while self.shell.recv_ready():
                _out(self.shell.recv(1024))

    def _cmd(self, command, answer='#\s$'):
        self._write(command)
        if answer:
            return self._wait_answer(answer)
        else:
            self._read_shell()

    def enable_cmd(self):
        self._write("enable")
        if self._wait_answer('Password:\s$'):
            if self._cmd(self.password):
                return True
        return False

    def exec_script(self, script):
        self._cmd(script)

    def no_pager(self):
        self._cmd("terminal pager 0")

    def write_config(self):
        self._cmd("write memory")

    def exit(self):
        self._cmd("exit", answer=None)
        self.close()

    def close(self):
        self.connected = False
        try:
            self.std_out.close()
            self.std_in.close()
            self.shell.close()
            self.client.close()
        except None:
            pass


def load_script(script_file):
    commands = "show clock"
    if os.path.isfile(script_file):
        fd = open(script_file,'r')
        commands = fd.read()
        fd.close()
    return commands


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=PROG_DESC)
    parser.add_argument('-c', '--hostname')
    parser.add_argument('-u', '--username')
    parser.add_argument('-p', '--password')
    parser.add_argument('-s', '--script', default='script.asa')
    parser.add_argument('-w', '--write', action='store_true', help="Write config")
    parser.add_argument('-C', '--check', action='store_true', help="Check connection")
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output")

    args = parser.parse_args()

    if args.hostname and args.username and args.password:
        if not args.check:
            enable_output = True
        ssh = ASAClient(args.hostname, args.username, args.password)
        if args.check:
            if ssh.connected:
                print("OK")
        else:
            ssh.enable_cmd()
            ssh.no_pager()
            ssh.exec_script(load_script(args.script))
        ssh.exit()
    else:
        parser.print_help()
