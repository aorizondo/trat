#!/usr/bin/python
# -*- coding: utf-8 -*-

from select import select
from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR, timeout
from jim.lib import App, Message, bytes_to_dict, dict_to_bytes, ExtraLog, ServerVerifier, ServerResponse, ServerStorage
from jim.app_config import *
from logs.server_log_config import server_logger
from threading import Thread
from queue import Queue
from time import sleep
import hashlib, binascii, random, string, hmac
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from os import listdir
from os.path import isfile
from pymongo import MongoClient


def login_required(fn):
    def wrapped(*args):
        for i in args:
            if isinstance(i, Server):
                srv = i
            if isinstance(i, socket):
                conn = i
        if srv and conn:
            if srv.socket_authorized(conn):
                return wrapped
            else:
                print('Connnection is not authenticated!')
                return None
    return wrapped


class MongoDbStorage:

    def __init__(self):
        try:
            self.client = MongoClient('{}:{}'.format(DEFAULT_HOST, MONGODB_PORT))
            self.db = self.client[MONGO_SRV_DB_NAME]
            self.messages = self.db.messages
            status = 'OK'
        except Exception as e:
            status = 'ERROR: ' + str(e)
        print('MongoDB status... ' + status)

    def store(self, data):
        if self.messages and isinstance(data, dict):
            print('MONGED: {}'.format(data))
            self.messages.insert_one(data)


class FtpDaemon:

    def __init__(self):
        self.daemon = None

    def run_in_thread(self):
        ftp_thread = Thread(target=self._run)
        ftp_thread.daemon = True
        ftp_thread.start()

    def _run(self):
        try:
            authorizer = DummyAuthorizer()
            # todo: make auth for every user
            authorizer.add_user('2aNTjQTyL8VY5zcUtF', '4Fa8PJCgQC3LUSZb4J', SRV_UPLOADS_DIR, perm='elradfmwMT')
            handler = FTPHandler
            handler.authorizer = authorizer
            self.daemon = FTPServer((DEFAULT_HOST, FTP_PORT), handler)
            self.daemon.max_cons = 256
            self.daemon.max_cons_per_ip = 5
            handler.banner = 'ftp-daemon is ready...'
            print(handler.banner)
            self.daemon.serve_forever()
        except Exception as e:
            print('i can''t run ftp daemon!', e)

    def stop(self):
        self.daemon.close()
        print('ftp daemon stopped')


class Server(metaclass=ServerVerifier):

    def __init__(self):

        print('{} server v.{}'.format(APP_NAME, APP_VERSION))

        self.port = DEFAULT_PORT
        self.host = DEFAULT_HOST
        self.logger = server_logger
        self._socket = None
        self.clients = []
        self.readers = []
        self.writers = []
        self.storage = ServerStorage()
        self._threads = []
        self._queue_in = Queue()
        self._queue_out = Queue()
        self.connected_users = {}
        self.authenticated_users = []
        self.ftp = None
        self.mongo = MongoDbStorage()

    def run_server(self, port=DEFAULT_PORT, host=DEFAULT_HOST):
        if port:
            self.port = port
        if host:
            self.host = host

        try:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.bind((self.host, self.port))
            sock.listen(10)
            sock.settimeout(0.3)
            self._socket = sock
            self.logger.info('App server started on {}:{}'.format(self.host, str(self.port)))

            self.ftp = FtpDaemon()
            self.ftp.run_in_thread()
            return True
            
        except Exception as e:
            self.logger.critical('Error. Can not start app server!')
            return False

    def wait_clients_and_sort_them(self):
        while True:
            sleep(1)
            try:
                conn, addr = self._socket.accept()
            except timeout:
                pass
            except OSError as err:
                print(err)
            else:
                self.clients.append(conn)
            finally:
                wait = 0
                try:
                    self.writers, self.readers, err = select(self.clients, self.clients, [], wait)
                except:
                    pass
                self._build_incoming_queue()

    def _build_incoming_queue(self):
        for conn in self.writers:
            raw_data = conn.recv(BUFFER_LENGTH)
            if raw_data:
                if bool(raw_data):
                    if isinstance(raw_data, bytes):
                        w_jmessage = bytes_to_dict(raw_data)
                        self._queue_in.put({WRITER_SOCKET: conn, WRITER_MESSAGE: w_jmessage})
                        print('QUEUED: {}'.format(w_jmessage))

    def process_in(self):
        while True:
            self._route_in()
            self.transfer_uploaded_images_to_db()

    def process_out(self):
        while True:
            self._route_out()

    def _route_in(self):
        sleep(1)
        if self._queue_in.not_empty:
            struct = self._queue_in.get()
            w_jmessage = struct[WRITER_MESSAGE]
            conn = struct[WRITER_SOCKET]

            print('PROCESSED: {}'.format(w_jmessage))

            cli_msg = Message(w_jmessage[ACTION])
            if cli_msg.action == QUIT:
                self.reset_socket(conn)
                return

            if MESSAGE in w_jmessage:
                cli_msg.message = w_jmessage[MESSAGE]
                # сохраним в mongodb
                if self.mongo:
                    self.mongo.store(w_jmessage)

            if USER_ID in w_jmessage:
                cli_msg.user = self.storage.get_user_by_id(w_jmessage[USER_ID])
            elif USER_LOGIN in w_jmessage:
                cli_msg.user = self.storage.get_user_by_login(w_jmessage[USER_LOGIN])

            if FRIEND_ID in w_jmessage:
                cli_msg.friend = self.storage.get_user_by_id(w_jmessage[FRIEND_ID])
            elif FRIEND_LOGIN in w_jmessage:
                cli_msg.friend = self.storage.get_user_by_login(w_jmessage[FRIEND_LOGIN])

            if PASSWORD in w_jmessage:
                cli_msg.password = w_jmessage[PASSWORD]

            action = cli_msg.action
            if action == MSG:
                if self.socket_authorized(conn):
                    if cli_msg.friend in self.connected_users:
                        destination_socket = self.connected_users[cli_msg.friend]
                        if destination_socket:
                            self._queue_out.put({DESTINATION_SOCKET: destination_socket, MSG: cli_msg})
                    else:
                        print('FRIEND IS OFFLINE: {}'.format(cli_msg.friend))
                else:
                    print('NOT AUTHORIZED TO SEND MESSAGES: {}'.format(cli_msg.user))
                    # retrieve auth
                    resp = dict_to_bytes({ACTION: AUTH, RESPONSE: NON_AUTH_CODE})
                    self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: resp})

            elif action == BROADCAST:
                if self.socket_authorized(conn):
                    if cli_msg.user and cli_msg.message:
                        self._queue_out.put({BROADCASTER: conn, MSG: cli_msg})
                    else:
                        resp = dict_to_bytes({ACTION: BROADCAST, RESPONSE: BAD_QUERY_CODE})
                        self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: resp})

            elif action == AUTH:
                response_code = None
                if self.socket_authorized(conn):  # auth already
                    response_code = OK_CODE
                else:
                    if hasattr(cli_msg, PASSWORD):
                        if bool(cli_msg.password):
                            check_hash = self.encrypt_string(cli_msg.password)
                            auth_ok = hmac.compare_digest(cli_msg.user.password, check_hash)
                            if auth_ok:
                                response_code = OK_CODE
                                self.authenticated_users.append(conn)
                                # обновим юзера в словаре подключенных сокетов
                                # т.к после презенс в юзере может быть NONE если входим из gui
                                self.del_from_connected(conn)
                                self.connected_users[cli_msg.user] = conn
                            else:
                                response_code = NON_VALID_CREDENTIALS_CODE
                if response_code:
                    resp = dict_to_bytes({ACTION: AUTH, RESPONSE: response_code})
                    self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: resp})

            elif action == PRESENCE:
                if self.socket_authorized(conn):  # auth already
                    self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: ServerResponse(cli_msg).build_response()})
                else:
                    if cli_msg.user:
                        hash = cli_msg.user.password
                        if not bool(hash):
                            # create pass
                            new_pass = self.generate_random_password()
                            # предполагается, что новый пароль сообщим юзеру на почту или смс
                            strpass = 'NEW PASS GENERATED: {} {}'.format(cli_msg.user, new_pass)
                            # запишу пока в файл, для отладки
                            with open('passwords.txt', 'a') as txt:
                                txt.write('\n'+strpass)

                            new_hash = self.encrypt_string(new_pass)
                            self.storage.set_user_hash(new_hash, user=cli_msg.user)

                        # retrieve auth
                        resp = dict_to_bytes({ACTION: AUTH, RESPONSE: NON_AUTH_CODE})
                        self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: resp})

                    if cli_msg.user not in self.connected_users:
                        # запомнить соответствие юзера и сокета
                        self.connected_users[cli_msg.user] = conn
                        self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: ServerResponse(cli_msg).build_response()})
                        return

            elif action in CONTACT_OPS:
                if self.socket_authorized(conn):
                    self._queue_out.put({DESTINATION_SOCKET: conn, RESPONSE: ServerResponse(cli_msg).build_response()})
                    return

    def _route_out(self):

        sleep(1)
        # отправить в нужный сокет по ид клиента
        if self._queue_out.not_empty:

            destination_sockets = []
            struct_out = self._queue_out.get()

            if MSG in struct_out or BROADCAST in struct_out:
                msg_out = struct_out[MSG]
            elif RESPONSE in struct_out:
                msg_out = struct_out[RESPONSE]
            else:
                msg_out = None

            if DESTINATION_SOCKET in struct_out:
                destination_sockets.append(struct_out[DESTINATION_SOCKET])
            elif WRITER_SOCKET in struct_out:
                destination_sockets.append(struct_out[WRITER_SOCKET])
            elif BROADCASTER in struct_out:
                destination_sockets = self.authenticated_users[:]
                destination_sockets.remove(struct_out[BROADCASTER])

            for destination_socket in destination_sockets:
                if destination_socket and msg_out:
                    if isinstance(msg_out, Message):
                        msg_out = msg_out.get_message_json()
                    print('SENDING TO USER: {}'.format(msg_out))
                    self.respond(destination_socket, msg_out)

    @ExtraLog(server_logger)
    def respond(self, conn, server_response):
        if isinstance(server_response, dict):
            server_response = dict_to_bytes(server_response)
        if isinstance(server_response, bytes):
            conn.send(server_response)

    def send_to_group(self, msg, group):
        pass

    @login_required
    @ExtraLog(server_logger)
    def probe_client(self, conn):
        self.respond(conn, Message(PROBE).get_message_json())

    def socket_authorized(self, sock):
        if isinstance(sock, socket):
            return sock in self.authenticated_users
        else:
            return False

    @ExtraLog(server_logger)
    def reset_socket(self, conn):
        if conn in self.clients:
            self.clients.remove(conn)
        if conn in self.writers:
            self.writers.remove(conn)
        if conn in self.readers:
            self.readers.remove(conn)
        if conn in self.authenticated_users:
            self.authenticated_users.remove(conn)
        self.del_from_connected(conn)
        conn.close()

    def del_from_connected(self, conn):
        # удалим подключенного юзера из словаря при сбросе
        inverted_cu = dict((v, k) for k, v in self.connected_users.items())
        user_to_reset = inverted_cu[conn]
        self.connected_users.pop(user_to_reset)
        print('DISCONNECTED: {}'.format(user_to_reset))

    @staticmethod
    def generate_random_password():
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
        size = random.randint(5, 6)
        return ''.join(random.choice(chars) for x in range(size))

    @staticmethod
    def encrypt_string(source_string):
        dk = hashlib.pbkdf2_hmac(
            SHA256,
            str(source_string).encode(DEFAULT_ENCODING),
            str(SALT).encode(DEFAULT_ENCODING),
            100000
        )
        return binascii.hexlify(dk).decode(DEFAULT_ENCODING)

    def __del__(self):
        if self._socket:
            self._socket.shutdown(SHUT_RDWR)
        if self.ftp:
            self.ftp.stop()

    def transfer_uploaded_images_to_db(self):
        user_dirs = listdir(SRV_UPLOADS_DIR)
        for udir in user_dirs:
            full_udir = os.path.join(SRV_UPLOADS_DIR, udir)
            uploaded_images = listdir(full_udir)
            if len(uploaded_images) > 0:
                for uimage in uploaded_images:
                    full_path = os.path.join(full_udir, uimage)
                    if isfile(full_path):
                        this_user = self.storage.get_user_by_login(udir)
                        if this_user:
                            self.storage.save_image_to_db(full_path, this_user, PROFILE_IMAGE)
                            os.remove(full_path)


if __name__ == '__main__':

    params = App().get_start_params()
    serv = Server()

    if serv.run_server(params['port'], params['addr']):
        print('I wait clients...')

        t = Thread(target=serv.process_in)
        t.daemon = True
        t.start()

        t1 = Thread(target=serv.process_out)
        t1.daemon = True
        t1.start()

        serv.wait_clients_and_sort_them()

    else:
        print('Server starting error!')