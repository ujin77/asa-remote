#!/usr/bin/python
# -*- coding: utf-8
#

import paramiko

CMD = """
show clock
exit
"""

HOST = '10.20.30.40'
USER = 'user'
PASS = 'pass'

def read_shell(shell):
    while shell.recv_ready():
        print(shell.recv(1024))


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=HOST, username=USER, password=PASS, look_for_keys=False)
shell = client.invoke_shell()
shell.settimeout(10)
stdin = shell.makefile('wb')
stdout = shell.makefile('rb')
read_shell(shell)
stdin.write(CMD)
print stdout.read()
stdout.close()
stdin.close()
shell.close()
client.close()
