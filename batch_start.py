#!/usr/bin/python
# -*- coding: utf-8 -*-

from subprocess import Popen
from time import sleep

processes = []

# for Linux only

usernames = ['Robert','Kelton','Carlos']
while True:
    sel = input("1. Start server + 3 clients (s) \n2. Stop all (x)\n")
    if sel == 's' or sel == '1':

        processes.append(Popen("x-terminal-emulator -e python3 server.py", shell=True))
        sleep(2)

        for u in usernames:
            processes.append(Popen("x-terminal-emulator -e python3 client.py -u {}".format(u), shell=True))
            sleep(1)

        processes.append(Popen("x-terminal-emulator -e python3 cli_ui.py", shell=True))

    elif sel == 'x' or sel == '2':
        for p in processes:
            p.kill()
        processes.clear()
        break
