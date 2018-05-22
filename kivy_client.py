#!/usr/bin/env python
# -*- coding: utf-8 -*-

from client import Client
from jim.app_config import *
from jim.lib import Message
from kivy.app import App
from kivy.properties import StringProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.clock import Clock
from threading import Thread


class Connected(Screen):

    contacts = ListProperty([])

    def __init__(self, *args, **kwargs):
        super(Connected, self).__init__(*args, **kwargs)
        self.client = None
        self.selected_friend_login = None
        self.selected_friend = None

        Clock.schedule_interval(self.check_incoming_messages, 1)

    def check_incoming_messages(self, dt):
        if self.client:
            if len(self.client.new_messages_arrived_from) > 0:
                self.change(self.selected_friend_login)

    def send_message(self):
        if self.client:
            msg_input = self.ids['tiMessage']
            msg_text = msg_input.text
            if self.selected_friend or self.selected_friend_login == COMMON_CHAT:
                if self.selected_friend_login == COMMON_CHAT:
                    msg = Message(BROADCAST, msg_text, self.client.user)
                else:
                    msg = Message(MSG, msg_text, self.client.user, self.selected_friend)
                if self.client.send(msg):
                    self.client.db.store_message(msg)
                msg_input.text = ''
                self.change(self.selected_friend_login)

    def change(self, change=None):
        if isinstance(change, str):
            self.selected_friend_login = change
        elif change is None:
            pass
        else:
            self.selected_friend_login = change.text
        chat_window = self.ids['tiChat']
        chat_window.text = ''

        if bool(self.selected_friend_login):
            self.client = self.parent.screens[0].cli
            cli = self.client
            if cli:
                if self.selected_friend_login in cli.new_messages_arrived_from:
                    cli.new_messages_arrived_from.remove(self.selected_friend_login)

                self.selected_friend = cli.db.get_user_by_login(self.selected_friend_login)
                if self.selected_friend or self.selected_friend_login == COMMON_CHAT:
                    self.selected_friend = self.selected_friend if self.selected_friend_login != COMMON_CHAT else None
                    messages = cli.db.get_local_messages(cli.user, self.selected_friend)
                    for i in messages:
                        stripped_message = cli.strip_tags(i[MESSAGE])
                        chat_window.text += '\n{}: {}'.format(i[USER_LOGIN].upper(), stripped_message)

    def disconnect(self):
        self.manager.transition = SlideTransition(direction='right')
        self.manager.current = 'login'
        self.manager.get_screen('login').reset_form()


class Login(Screen):

    def __init__(self, *args, **kwargs):
        self.cli = None
        super(Login, self).__init__(*args, **kwargs)

    def do_login(self, login_text, password_text):
        app = App.get_running_app()

        if bool(login_text) and bool(password_text):
            trat.cli = Client()
            self.cli = trat.cli

            if self.cli.connect():
                self.cli.reg_presence()

            app.username = login_text
            app.password = password_text

            user = self.cli.db.get_user_by_login(app.username)
            if user:
                self.cli.user = user
                self.cli.auth_request(app.password)
                if self.cli.authenticated:
                    print('KIVY AUTH OK')
                    lvContacts = self.manager.screens[1].ids.lvContacts
                    lvContacts.item_strings.clear()
                    lvContacts.item_strings.append(COMMON_CHAT)

                    friend_list = self.cli.sync_remote_contacts()
                    if len(friend_list) > 0:
                        if DATA in friend_list:
                            data = friend_list[DATA]
                            if data:
                                for f in data:
                                    lvContacts.item_strings.append(f[FRIEND_LOGIN])

                    trat.title += ' : ' + app.username
                    self.manager.transition = SlideTransition(direction='left')
                    self.manager.current = 'connected'

                    t1 = Thread(target=self.cli.go_reader_state)
                    t1.daemon = True
                    t1.start()

    def reset_form(self):
        self.ids['login'].text = ''
        self.ids['password'].text = ''


class LoginApp(App):
    kv_directory = 'templates'
    username = StringProperty(None)
    password = StringProperty(None)

    def build(self):
        self.title = '{} v.{}'.format(APP_NAME, APP_VERSION)
        manager = ScreenManager()
        manager.add_widget(Login(name='login'))
        manager.add_widget(Connected(name='connected'))
        return manager


if __name__ == '__main__':
    trat = LoginApp()
    trat.run()