#!/usr/bin/python
# -*- coding: utf-8
#

import paramiko
import os, sys, time
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
    response = ''
    connected = False

    def __init__(self, hostname, username, passwd):
        super(ASAClient, self).__init__()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname=hostname, username=username, password=passwd, look_for_keys=False, timeout=3)
        self.password = passwd
        self.shell = self.client.invoke_shell()
        self.shell.settimeout(3)
        self.stdin = self.shell.makefile('wb')
        self.stdout = self.shell.makefile('rb')
        if not self._wait_answer('(\>|#)\s'):
            self.close()
        else:
            self.connected = True

    def _wait_data_from_shell(self):
        timeout = self.data_timeout * 10
        while timeout and not self.shell.recv_ready():
            timeout -= 1
            time.sleep(.1)
            # print('Data timeout:', timeout)
        if timeout:
            return True
        print('Data timeout:', self.data_timeout, 'sec')
        return False

    def _is_answer(self, pattern):
        self._wait_data_from_shell()
        if self.shell.recv_ready():
            answer = self.shell.recv(1024)
            _out(answer)
            if re.search(pattern, answer):
                return True
        return False

    def _wait_answer(self, pattern):
        timeout = self.answer_timeout * 10
        self.response = ''
        while timeout and not self._is_answer(pattern):
            timeout -= 1
            time.sleep(.1)
        if timeout:
            return True
        print('Answer timeout:', self.answer_timeout, 'sec')
        return False

    def _read_shell(self):
        self._wait_data_from_shell()
        while self.shell.recv_ready():
            _out(self.shell.recv(1024))

    def enable_cmd(self):
        self.stdin.write("enable\n")
        if self._wait_answer('Password:\s$'):
            self.stdin.write(self.password)
            self.stdin.write("\n")
            if self._wait_answer('#\s$'):
                return True
        return False

    def exec_cmd(self, script):
        self.stdin.write(script)
        self.stdin.write("\n")
        if not self._wait_answer('#\s$'):
            print "Script timeout"

    def no_pager(self):
        self.stdin.write("terminal pager 0\n")
        self._wait_answer('#\s$')

    def write_config(self):
        self.stdin.write("write config\n")
        self._wait_answer('#\s$')

    def exit(self):
        self.stdin.write("exit\n")
        self._read_shell()
        self.close()

    def close(self):
        self.connected = False
        self.stdout.close()
        self.stdin.close()
        self.shell.close()
        self.client.close()


def load_script(script_file):
    commands = "show clock\n"
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
            ssh.exec_cmd(load_script(args.script))
        ssh.exit()
    else:
        parser.print_help()
