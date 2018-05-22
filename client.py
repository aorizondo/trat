#!/usr/bin/python
# -*- coding: utf-8 -*-

from socket import socket, AF_INET, SOCK_STREAM
from jim.lib import App, Message, bytes_to_dict, ExtraLog, ClientVerifier, ClientStorage, FriendList, get_random_user
from jim.app_config import *
from logs.client_log_config import client_logger
from threading import Thread
from queue import Queue
from time import sleep
from getpass import getpass
import re


class Client(metaclass=ClientVerifier):

    def __init__(self, _user=None):
        self._socket = None
        self._server_response = None
        self.port = DEFAULT_PORT
        self.host = DEFAULT_HOST
        self.logger = client_logger
        self.db = ClientStorage(server_side=False)
        self.contacts = FriendList()
        self.registered = False
        self.updated = False
        self.authenticated = False
        self._queue_in = Queue()
        self.user = _user
        # список контактов от которых есть непрочитанные сообщения
        self.new_messages_arrived_from = []

    @ExtraLog(client_logger)
    def connect(self, port=DEFAULT_PORT, host=DEFAULT_HOST):
        if port:
            self.port = port
        if host:
            self.host = host
        try:
            self._socket = socket(AF_INET, SOCK_STREAM)
            self._socket.connect((self.host, self.port))
            self._socket.settimeout(3)
            return True
        except:
            self.logger.critical('Error. Can not establish server connection!')
            return False

    @ExtraLog(client_logger)
    def send(self, message):
        try:
            need_byted = False if isinstance(message, bytes) else True
            jmessage = message.get_message_json(byted=need_byted)
            self._socket.send(jmessage)
        except:
            self.close()
            return False
        else:
            return True

    @staticmethod
    def strip_tags(text):
        return re.sub(r'<.*?>|p, li { white-space: pre-wrap; }', '', text).strip()

    @ExtraLog(client_logger)
    def receive(self):
        try:
            self._server_response = bytes_to_dict(self._socket.recv(BUFFER_LENGTH))
        except:
            return

        if MESSAGE in self._server_response:
            cleaned_text = self.strip_tags(self._server_response[MESSAGE])
            print('MESSAGE FROM {}: {}'.format(self._server_response[USER_LOGIN], cleaned_text))
            # return
        elif ACTION in self._server_response:
            if self._server_response[ACTION] == ADD_CONTACT:
                if self._server_response[RESPONSE] == OBJECT_CREATED_CODE:
                    flogin = self._server_response[FRIEND_LOGIN]
                    print('{} is your friend now!'.format(flogin))
                    self.updated = False
                else:
                    print('! Friend <{}> does not exist'.format(self._server_response[FRIEND_LOGIN]))

            elif self._server_response[ACTION] == DEL_CONTACT:
                if self._server_response[RESPONSE] == OK_CODE:
                    flogin = self._server_response[FRIEND_LOGIN]
                    print('{} is removed from your friends!'.format(flogin))
                    self.updated = False

            elif self._server_response[ACTION] == AUTH:
                if self._server_response[RESPONSE] == OK_CODE:
                    self.authenticated = True
                    print('AUTH OK')
                    return
                else:
                    self.authenticated = False

            else:
                self.registered = self._server_response[ACTION] == PRESENCE and self._server_response[RESPONSE] == ACCEPTED_CODE

        return self._server_response

    def friend_list_request(self):
        self.send(Message(GET_CONTACTS, None, self.user))
        return self.receive()

    def add_friend_request(self, friend_login):
        if friend_login:
            self.send(Message(ADD_CONTACT, None, self.user, self.friend))
            return self.receive()

    def del_friend_request(self, friend_login):
        if friend_login:
            self.send(Message(DEL_CONTACT, None, self.user, self.friend))
            return self.receive()

    def reg_presence(self):
        self.send(Message(PRESENCE, None, self.user))
        return self.receive()

    def disconnect(self):
        self.send(Message(QUIT, None, self.user))
        self.close()

    def auth_request(self, password, _user=None):
        if not _user:
            _user = self.user
        if bool(password):
            self.send(Message(AUTH, None, _user, None, password))
            return self.receive()

    def update_local_contacts(self):
        fl = self.friend_list_request()
        if fl:
            self.db.update_local_contacts(fl)

    def go_reader_state(self):
        while True:
            sleep(1)
            try:
                srv_msg = self.receive()
                if srv_msg:
                    print('INCOMING: ', srv_msg)
                    self._queue_in.put({DATA: srv_msg, 'incoming': True})
                    self.write_messages_queue_to_db()
            except Exception as e:
                print(e)

    def write_messages_queue_to_db(self):
        try:
            if self._queue_in.not_empty:
                srv_msg = self._queue_in.get()
                self.db.store_message(srv_msg)

                # удалю проверенный на сервере добавленный контакт из временной таблицы
                if ADD_CONTACT in srv_msg and FRIEND_LOGIN in srv_msg:
                    if srv_msg[RESPONSE] == OBJECT_CREATED_CODE:
                        # todo: BUG. not clean!
                        self.db.del_non_verified(srv_msg[FRIEND_LOGIN])
                        print('REMOVED FROM TEMP: {}'.format(srv_msg[FRIEND_LOGIN]))

                # добавлю в список непрочитанных
                if DATA in srv_msg:
                    direction = 'incoming'
                    if direction in srv_msg:
                        if srv_msg[direction]:
                            srv_msg = srv_msg[DATA]
                            if USER_LOGIN in srv_msg:
                                sender_login = srv_msg[USER_LOGIN]
                                if bool(sender_login):
                                    self.new_messages_arrived_from.append(sender_login)

        except Exception as e:
            print(e)

    def sync_remote_contacts(self):
            remote_friend_list = self.friend_list_request()
            if remote_friend_list:
                self.db.update_local_contacts(remote_friend_list, self.user)
                self.updated = True
            return remote_friend_list

    def close(self):
        if self._socket:
            self._socket.close()

    def __del__(self):
        self.close()


if __name__ == '__main__':

    params = App().get_start_params()
    if params['username']:
        db = ClientStorage(server_side=False)
        user = db.get_user_by_login(params['username'])
        if user:
            IAM = user

    cli = Client()
    if cli.connect(params['port'],params['addr']):
        print(HELP_CLI)
        print('Im client: {} {}'.format(cli.user.user_id, cli.user.login))

        cli.reg_presence()

        t1 = Thread(target=cli.go_reader_state)
        t1.daemon = True
        t1.start()

        while True:
            sleep(1)
            if cli.authenticated:
                if cli.registered:
                    if not cli.updated:
                        cli.sync_remote_contacts()
                    else:
                        user_input = input('(chat) >')
                        args = user_input.split()

                        if user_input.startswith('message'):
                            to = args[1]
                            # todo: take all words
                            msg_text = args[2]

                            if bool(msg_text):
                                friend = cli.db.get_user_by_login(to)
                                if friend:
                                    msg = Message(MSG, msg_text, cli.user, friend)
                                    if cli.send(msg):
                                        cli.db.store_message(msg)
                                else:
                                    print('! There is no user with name: {}'.format(to))
                        elif user_input.startswith('list'):
                            res = cli.contacts.get_friends(user=IAM)
                            for friend in res[IAM]:
                                print(friend.user_id, friend.login)
                        elif user_input.startswith('quit'):
                            cli.disconnect()
                            break
                        elif user_input.startswith('help') or user_input.startswith('?'):
                            print(HELP_CLI)
                        elif user_input.startswith('add'):
                            friend_name = args[1]
                            if bool(friend_name):
                                friend = cli.db.add_non_verified(friend_name)
                                if friend:
                                    cli.send(Message(ADD_CONTACT, None, cli.user, friend))
                        elif user_input.startswith('del'):
                            friend_name = args[1]
                            if bool(friend_name):
                                cli.send(Message(DEL_CONTACT, None, cli.user, friend))

                        cli.write_messages_queue_to_db()

                else:  # non reg
                    cli.reg_presence()

            else:  # non auth
                cli.auth_request(getpass())