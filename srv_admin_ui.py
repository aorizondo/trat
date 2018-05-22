#!/usr/bin/python
# -*- coding: utf-8 -*-

from ui.ui_classes import ChatDesktopGUI

if __name__ == '__main__':

    ui = ChatDesktopGUI(cli=None)
    ui.show_main_form(title='Messenger|Server admin')
    ui.refresh_srv_connect_list()
    ui.start_app()