#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from sqlalchemy import create_engine

# general
APP_NAME = 'Trat'
APP_VERSION = '0.9'

COMMON_CHAT = '* CHAT FOR ALL *'

# dirs
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILE_DIR = os.path.join(BASE_DIR, 'profile')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
ICONS_DIR = os.path.join(BASE_DIR, 'icons')
SRV_UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')

# network settings
DEFAULT_ENCODING = 'utf-8'
DEFAULT_PORT = 7763
DEFAULT_HOST = '127.0.0.1'
BUFFER_LENGTH = 5122
SERVER_THREADS_NUM = 3
FTP_PORT = 9960
MONGODB_PORT = 27017

# meta restrictions
SERVER_FORBIDDEN_USES = ('connect',)
CLIENT_FORBIDDEN_USES = ('accept', 'listen') 

# protocol actions
PRESENCE = 'presence'
PROBE = 'probe'
MSG = 'msg'
QUIT = 'quit'
JOIN = 'join'
LEAVE = 'leave'
AUTH = 'authenticate'
BROADCAST = 'broadcast'

GET_CONTACTS = 'get_contacts'
CONTACT_LIST = 'contact_list'
ADD_CONTACT = 'add_contact'
DEL_CONTACT = 'del_contact'

CONTACT_OPS = [GET_CONTACTS, CONTACT_LIST, ADD_CONTACT, DEL_CONTACT]
ALLOWED_ACTIONS = [PRESENCE, PROBE, MSG, QUIT, AUTH, JOIN, LEAVE] + CONTACT_OPS

# server response codes
BASE_NOTICE_CODE = 100
IMPORTANT_NOTICE_CODE = 101
OK_CODE = 200
OBJECT_CREATED_CODE = 201
ACCEPTED_CODE = 202
BAD_QUERY_CODE = 400
NON_AUTH_CODE = 401
NON_VALID_CREDENTIALS_CODE = 402
FORBIDDEN_CODE = 403
NOT_FOUND_CODE = 404
CONFLICT_CODE = 409
OFFLINE_CODE = 410
SERVER_ERROR_CODE = 500

# server codes structured
RESPONSE = 'response'
MESSAGE = 'message'
ACTION = 'action'
TIME = 'time'
ALERT = 'alert'
ERROR = 'error'
USER_LOGIN = 'user_login'
FRIEND_LOGIN = 'friend_login'
USER_ID = 'user_id'
FRIEND_ID = 'friend_id'
QUANTITY = 'quantity'

OK_STRUCT = {RESPONSE: OK_CODE, ALERT: 'Success!'}
SERVER_ERROR_STRUCT = {RESPONSE: SERVER_ERROR_CODE, ERROR: 'Server error happened'}
WRONG_REQUEST_STRUCT = {RESPONSE: BAD_QUERY_CODE, ERROR: 'Wrong data rejected'}

SERVER_RESPONSES_DICT = {
    BASE_NOTICE_CODE: None,
    IMPORTANT_NOTICE_CODE: None,
    OK_CODE: OK_STRUCT,
    OBJECT_CREATED_CODE: None,
    ACCEPTED_CODE: None,
    BAD_QUERY_CODE: WRONG_REQUEST_STRUCT,
    NON_AUTH_CODE: None,
    NON_VALID_CREDENTIALS_CODE: None,
    FORBIDDEN_CODE: None,
    NOT_FOUND_CODE: None,
    CONFLICT_CODE: None,
    OFFLINE_CODE: None,
    SERVER_ERROR_CODE: SERVER_ERROR_STRUCT,
}

# service usage
DATA = 'data'
DATE = 'date'
USERLIST = 'userlist'
USER = 'user'
WRITER_SOCKET = 'wr_sock'
DESTINATION_SOCKET = 'destination_sock'
BROADCASTER = 'broadcaster'
WRITER_MESSAGE = 'wr_msg'
FRIEND = 'friend'
PASSWORD = 'password'

# security
SHA256 = 'sha256'
SECRET_KEY = b'GE.>^d8xyWe{aDvYFS%NHHZO$}3)At'
SALT = 'vhxfDgbM8VP94kCLdGNmHGxbReJMk6qe'

# datebase
DB_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))
SERVER_DB_PATH = os.path.join(DB_FOLDER_PATH, 'server.db')
SERVER_DB_ENGINE = create_engine('sqlite:///{}'.format(SERVER_DB_PATH), connect_args={'check_same_thread': False}, echo=False)
CLIENT_DB_PATH = os.path.join(DB_FOLDER_PATH, 'client.db')
CLIENT_DB_ENGINE = create_engine('sqlite:///{}'.format(CLIENT_DB_PATH), connect_args={'check_same_thread': False}, echo=False)
MONGO_SRV_DB_NAME = 'trat'

# visual
AVATAR_PATH = os.path.join(PROFILE_DIR, 'avatar.jpg')
DEFAULT_AVATAR_PATH = os.path.join(ICONS_DIR, 'anonymous.png')
PROFILE_IMAGE = 'avatar'

LOGO = '''

████████╗██████╗  █████╗ ████████╗
╚══██╔══╝██╔══██╗██╔══██╗╚══██╔══╝
   ██║   ██████╔╝███████║   ██║   
   ██║   ██╔══██╗██╔══██║   ██║   
   ██║   ██║  ██║██║  ██║   ██║   
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   

'''

HELP_CLI = '''
{}

{} v.{}

COMMANDS:
-------------------------
list :get contacts
message [friend] [text] :send message
add [friend] :add friend
del [friend] :del friend
quit :leave chat
-------------------------
'''.format(LOGO, APP_NAME, APP_VERSION)

# style colors
TURQUOISE = '#1abc9c'
GREEN_SEA = '#16a085'
WET_ASPHALT = '#34495e'
MIDNIGHT_BLUE = '#2c3e50'
POMEGRANTE = '#c0392b'
ALIZARN = '#e74c3c'
PETER_RIVER = '#3498db'
BELIZE_HOLE = '#2980b9'
AMETHYST = '#9b59b6'
WISTERIA = '#8e44ad'
EMERALD = '#2ecc71'
NEPHRITIS = '#27ae60'
SUN_FLOWER = '#f1c40f'
CLOUDS = '#ecf0f1'
SILVER = '#bdc3c7'
CONCRETE = '#95a5a6'
CARROT = '#e67e22'
ORANGE = '#f39c12'

# smiles coding
SMILES_ENCODER = {'happy.png': ':)', 'sad.png': ':(', 'angry.png': ':#'}
SMILES_DECODER = dict((v, k) for k, v in SMILES_ENCODER.items())
