#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ui.ui_classes import ChatDesktopGUI
from client import Client
from threading import Thread


if __name__ == '__main__':

    cli = Client()
    if cli.connect():

        cli.reg_presence()

        t1 = Thread(target=cli.go_reader_state)
        t1.daemon = False
        t1.start()

        ui = ChatDesktopGUI(cli=cli)
        ui.show_main_form()

        if cli.authenticated:
            ui.main_screen_show()
        else:
            ui.auth_screen_show()

        ui.start_app()

