#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse, json, time, dis
from jim.app_config import *
from server_errors import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy import or_, and_
from srv_models import User, UserFriend, UserHistory, Action, Group, GroupMembership, ServerImages
from cli_models import ClientFriends, ClientMessages, LocalUser, NonVerifiedContacts, LocalImages
from ftplib import FTP


class MetaVerifier(type):

    def __init__(cls, clsname, bases, clsdict):
        socket_used = False

        if cls.im_server:
            forbidden_uses = SERVER_FORBIDDEN_USES
        else:
            forbidden_uses = CLIENT_FORBIDDEN_USES

        for name,func in clsdict.items():
            bytecode = dis.Bytecode(func)

            for instr in bytecode:
                if instr.opname == 'LOAD_ATTR' and instr.argrepr in forbidden_uses:
                    raise IllegalCall(instr.argrepr, clsname)
                if instr.opname == 'LOAD_GLOBAL' and instr.argrepr == 'socket':
                    socket_used = True

        if cls.im_server and not socket_used:
            raise MissedMandatoryUsing('socket', clsname)


class ClientVerifier(MetaVerifier):
    def __init__(self,*args, **kwargs):
        self.im_server = False


class ServerVerifier(MetaVerifier):
    def __init__(self,*args, **kwargs):
        self.im_server = True


class ExtraLog:
    def __init__(self, logger):
        self.logger = logger

    def __call__(self, func):
        def decorated(*args, **kwargs):
            res = func(*args, **kwargs)
            self.logger.info('extra log: {}({}, {}) = {}'.format(func.__name__, args, kwargs, res))
            return res

        return decorated


class App:
    @staticmethod
    def _create_parser():
        prs = argparse.ArgumentParser()
        prs.add_argument('-p', '--port', type=int)
        prs.add_argument('-a', '--addr', type=str)
        prs.add_argument('-u', "--username", type=str)
        return prs

    def get_start_params(self):
        namespace = self._create_parser().parse_args()
        return {'port': namespace.port, 'addr': namespace.addr, 'username': namespace.username}


class Message:
    def __init__(self, action=None, message_txt=None, user=None, friend=None, password=None):
        self.action = action
        self.time = time.time()
        self.user = user
        self.friend = friend
        self.password = password

        if message_txt:
            self.message = message_txt.strip()
            if bool(self.message):
                if len(self.message) > 500:
                    self.message = self.message[0:499]

    def get_message_json(self, byted=True):
        mess_dict = {
            ACTION: self.action,
            TIME: self.time,
        }

        if hasattr(self, MESSAGE):
            if len(self.message) > 0:
                mess_dict[MESSAGE] = self.message
            
        if self.user:
            if self.action != ADD_CONTACT:
                mess_dict[USER_ID] = self.user.user_id
            mess_dict[USER_LOGIN] = self.user.login
            
        if bool(self.friend):
            if self.action != ADD_CONTACT:
                mess_dict[FRIEND_ID] = self.friend.user_id
            mess_dict[FRIEND_LOGIN] = self.friend.login

        if bool(self.password):
            mess_dict[PASSWORD] = self.password

        if byted:
            mess_dict = dict_to_bytes(mess_dict)

        return mess_dict

    def no_problem(self):
        if self.action == PROBE:
            return True
        elif self.action == PRESENCE:
            return bool(self.user)

        if hasattr(self, MESSAGE):
            if bool(self.message):
                if len(self.message) > 0 and self.action in ALLOWED_ACTIONS:
                    return True
        if hasattr(self, USER) and hasattr(self, FRIEND):
            if self.user != self.friend:
                return True
        return False


class ServerResponse:

    def __init__(self, cli_request):
        self.time = time.time()
        self.response_code = 200
        self._friendlist = None
        self.cli_request = cli_request

    def build_response(self):
        
        if not self.cli_request.no_problem():
            resp = SERVER_RESPONSES_DICT[BAD_QUERY_CODE]
        else:
            action = self.cli_request.action
            if action in CONTACT_OPS:
                self._friendlist = FriendList()

                if action == GET_CONTACTS:
                    user_friends = self._friendlist.get_friends(user=self.cli_request.user)
                    userlist = []
                    for user, friends in user_friends.items():
                        datalist = []
                        if user not in userlist:
                            userlist.append({USER_ID: user.user_id, USER_LOGIN: user.login})
                        for friend in friends:
                            if friend not in userlist:
                                userlist.append({USER_ID: friend.user_id, USER_LOGIN: friend.login})
                            datalist.append({ACTION: CONTACT_LIST, USER_LOGIN: user.login, USER_ID: user.user_id, FRIEND_LOGIN: friend.login, FRIEND_ID: friend.user_id})
                        resp = {USERLIST: userlist, RESPONSE: ACCEPTED_CODE, QUANTITY: len(friends), DATA: datalist}

                elif action == ADD_CONTACT:
                    if hasattr(self.cli_request, FRIEND):
                        if self._friendlist.add_friend(self.cli_request.user.login, self.cli_request.friend.login):
                            response_code = OBJECT_CREATED_CODE
                        else:
                            response_code = BAD_QUERY_CODE
                    else:
                        response_code = BAD_QUERY_CODE
                    resp = {ACTION: ADD_CONTACT, FRIEND_LOGIN: self.cli_request.friend.login, RESPONSE: response_code}

                elif action == DEL_CONTACT:
                    if hasattr(self.cli_request, FRIEND):
                        if self._friendlist.del_friend(self.cli_request.user.login, self.cli_request.friend.login):
                            response_code = OK_CODE
                        else:
                            response_code = BAD_QUERY_CODE
                    else:
                        response_code = BAD_QUERY_CODE
                    resp = {ACTION: DEL_CONTACT, FRIEND_LOGIN: self.cli_request.friend.login, RESPONSE: response_code}

            elif action == MSG:
                resp = self.cli_request.get_message_json(byted=False)
            elif action == PRESENCE:
                resp = {ACTION: PRESENCE, RESPONSE: ACCEPTED_CODE}

        print('SERV RESP BUILT:{}'.format(resp))

        return dict_to_bytes(resp)


class StorageBase:

    def __init__(self, server_side=True):
        self.server_side = server_side
        if self.server_side:
            engine = SERVER_DB_ENGINE
        else:
            engine = CLIENT_DB_ENGINE

        sess = sessionmaker(engine)
        self.session = sess()

    def __del__(self):
        if self.session is not None:
            try:
                self.session.close()
            except:
                pass

    def _commit(self):
        self.session.commit()

    def _add_to_session(self, obj):
        self.session.add(obj)
        self._commit()

    def get_user_table_class(self):
        return User if self.server_side else LocalUser

    def get_friends_table_class(self):
        return UserFriend if self.server_side else ClientFriends

    def get_images_table_class(self):
        return ServerImages if self.server_side else LocalImages

    def add_user(self, login, password=None, info=None, local_user_id=None, owner_id=None):
        if self.server_side:
            self._add_to_session(User(login, None, info))
        else:
            self._add_to_session(LocalUser(local_user_id, login, owner_id))

    def get_user_by_login(self, login):
        user_table = self.get_user_table_class()
        return self.session.query(user_table).filter(user_table.login == login).first()

    def get_user_by_id(self, id):
        user_table = self.get_user_table_class()
        return self.session.query(user_table).filter(user_table.user_id == id).first()

    def get_all_users(self):
        user_table = self.get_user_table_class()
        return self.session.query(user_table).all()

    def save_image_to_db(self, image_path, user=None, comment=''):
        if bool(image_path):
            if os.path.exists(image_path):
                images_table = self.get_images_table_class()
                with open(image_path, 'rb') as f:
                    img = f.read()
                self._add_to_session(images_table(image_data=img, user_id=user.user_id, comment=comment))

    def del_user_avatars(self, user):
        if user:
            images_table = self.get_images_table_class()
            self.session.query(images_table)\
                .filter(images_table.comment == PROFILE_IMAGE)\
                .filter(images_table.user_id == user.user_id).delete()
            self._commit()

    def extract_user_avatar(self, user, avatar_path=''):
        if not bool(avatar_path):
            avatar_path = AVATAR_PATH
        if user:
            images_table = self.get_images_table_class()
            blob = self.session.query(images_table)\
                .filter(images_table.comment == PROFILE_IMAGE)\
                .filter(images_table.user_id == user.user_id).first()
            if blob:
                with open(avatar_path, 'wb') as output_file:
                    output_file.write(blob.image_data)


class ServerStorage(StorageBase):

    def add_action(self, name):
        self._add_to_session(Action(name))

    def add_group(self, name):
        self._add_to_session(Group(name))

    def get_group_by_id(self, id):
        return self.session.query(Group).filter(Group.group_id == id).first()

    def user_exist(self, login):
        return self.session.query(User).filter(User.login == login).count() > 0

    def add_to_group(self, user, group):
        self._add_to_session(GroupMembership(user, group))

    def add_user_history_record(self, user_id, ip, action):
        self._add_to_session(UserHistory(user_id, ip, action))

    def set_user_hash(self, new_hash, **kwargs):
        user = None
        for key in kwargs:
            if key == USER_ID:
                user = self.get_user_by_id(kwargs[key])
            elif key == USER_LOGIN:
                user = self.get_user_by_login(kwargs[key])
            elif key == USER:
                user = kwargs[key]
        if isinstance(user, User):
            if bool(new_hash):
                id = user.user_id
                self.session.query(User).filter(User.user_id == id). \
                    update({'password': new_hash}, synchronize_session=False)
                self._commit()


class ClientStorage(StorageBase):

    def add_local_user(self, user_id, user_login, owner_id):
        self.add_user(user_login, None, None, user_id, owner_id)

    def add_local_contact(self, user_id, friend_id):
        self._add_to_session(ClientFriends(user_id, friend_id))

    def add_non_verified(self, login):
        non_verified = self.get_non_verified_contact(login)
        if isinstance(non_verified, NonVerifiedContacts):
            return non_verified
        else:
            self._add_to_session(NonVerifiedContacts(login))
            return self.get_non_verified_contact(login)

    def del_non_verified(self, login):
        if bool(login):
            if self.get_non_verified_contact(login):
                self.session.query(NonVerifiedContacts).filter(NonVerifiedContacts.login == login).delete()
                self._commit()

    def get_non_verified_contact(self, login):
        return self.session.query(NonVerifiedContacts).filter(NonVerifiedContacts.login == login).first()

    def _drop_local_contacts(self, iam):
        self.session.query(LocalUser).filter(LocalUser.owner_id == iam.user_id).delete()
        self.session.query(ClientFriends).filter(ClientFriends.user_id == iam.user_id).delete()
        self._commit()

    def update_local_contacts(self, flist, iam):
        if flist:
            self._drop_local_contacts(iam)
            for i in flist[USERLIST]:
                self.add_local_user(i[USER_ID], i[USER_LOGIN], iam.user_id)
            for i in flist[DATA]:
                self.add_local_contact(i[USER_ID], i[FRIEND_ID])

    def store_message(self, msg):
        is_incoming = False
        if isinstance(msg, Message):
            if hasattr(msg, MESSAGE) and hasattr(msg, USER) and hasattr(msg, FRIEND):
                if msg.friend:
                    self._add_to_session(ClientMessages(msg.user.user_id, msg.friend.user_id, msg.message))
                else:
                    self._add_to_session(ClientMessages(msg.user.user_id, None, msg.message))
        elif isinstance(msg, dict):
            if DATA in msg:
                msg = msg[DATA]
                is_incoming = True
            if MESSAGE in msg and USER_ID in msg:
                friend_id = msg[FRIEND_ID] if FRIEND_ID in msg else None
                self._add_to_session(ClientMessages(msg[USER_ID], friend_id, msg[MESSAGE], incoming=is_incoming))

    def get_local_messages(self, user, friend=None):
        mlist = []
        rows = None

        if user and friend:
            rows = self.session.query(ClientMessages) \
                .filter(or_(and_(ClientMessages.user_id == user.user_id, ClientMessages.friend_id == friend.user_id, ClientMessages.incoming == False),
                            and_(ClientMessages.user_id == friend.user_id, ClientMessages.friend_id == user.user_id, ClientMessages.incoming == True)))
        elif user:  # broadcast
            rows = self.session.query(ClientMessages) \
                .filter(or_(and_(ClientMessages.user_id == user.user_id, ClientMessages.friend_id == None, ClientMessages.incoming == False),
                            and_(ClientMessages.user_id != user.user_id, ClientMessages.friend_id == None, ClientMessages.incoming == True)))

        if rows:
            for row in rows:
                from_login = self.get_user_by_id(row.user_id).login
                mlist.append({DATE: row.added_date, MESSAGE: row.message, USER_LOGIN: from_login})

        return mlist

    def get_non_verified_contact_list(self):
        clist = []
        rows = self.session.query(NonVerifiedContacts).all()
        for row in rows:
            clist.append(row.login)
        return clist


class FriendList(StorageBase):

    def add_friend(self, user_login, friend_login):
        res = True
        if user_login and friend_login and user_login != friend_login:
            if not self.are_friends(user_login, friend_login):
                friend = self.get_user_by_login(friend_login)
                if friend:
                    user = self.get_user_by_login(user_login)
                    if user:
                        self._add_to_session(UserFriend(user_id=user.user_id, friend_id=friend.user_id))
                    else:
                        res = False
                else:
                    res = False
        else:
            res = False
        return res

    def are_friends(self, user_login, friend_login):
        if user_login and friend_login:
            friend = self.get_user_by_login(friend_login)
            if friend:
                friend_list = self.get_friends(user_login=user_login)
                if len(friend_list) > 0:
                    return friend in friend_list
        return False

    def del_friend(self, user_login, friend_login):
        res = True
        friend = self.get_user_by_login(friend_login)
        if friend:
            user = self.get_user_by_login(user_login)
            if user:
                query = self.session.query(UserFriend) \
                    .filter(UserFriend.user_id == user.user_id) \
                    .filter(UserFriend.friend_id == friend.user_id) \
                    .first()
                self.session.delete(query)
                self._commit()
            else:
                res = False
        else:
             res = False
        return res

    def get_friends(self, **kwargs):
        user = None
        for key in kwargs:
            if key == USER_ID:
                user = self.get_user_by_id(kwargs[key])
            elif key == USER_LOGIN:
                user = self.get_user_by_login(kwargs[key])
            elif key == USER:
                user = kwargs[key]
        flist = []
        if user:
            friends_table = self.get_friends_table_class()
            rows = self.session.query(friends_table) \
                .filter(friends_table.user_id == user.user_id)
            for row in rows:
                flist.append(self.get_user_by_id(row.friend_id))
        return {user: flist}


class FtpClient:

    def __init__(self):
        self.ftp = FTP()
        print(self.ftp.connect(DEFAULT_HOST, FTP_PORT))
        print(self.ftp.login('2aNTjQTyL8VY5zcUtF', '4Fa8PJCgQC3LUSZb4J'))

    def uploadFile(self, file_path, dir_name):
        if not dir_name in self.ftp.nlst():
            self.ftp.mkd(dir_name)
        self.ftp.cwd(dir_name)
        self.ftp.retrlines('LIST')
        self.ftp.storbinary('STOR ' + os.path.basename(file_path), open(file_path, 'rb'))
        self.ftp.quit()


# functions
def dict_to_bytes(message_dict):
    if isinstance(message_dict, dict):
        jmessage = json.dumps(message_dict)
        bmessage = jmessage.encode(DEFAULT_ENCODING)
        return bmessage
    else:
        raise TypeError


def bytes_to_dict(message_bytes):
    if isinstance(message_bytes, bytes):
        jmessage = message_bytes.decode(DEFAULT_ENCODING)
        message = json.loads(jmessage)
        if isinstance(message, dict):
            return message
        else:
            raise TypeError
    else:
        raise TypeError

# testing purpose
def get_random_user():
    import random
    friend = None
    user = ServerStorage().get_user_by_id(random.randrange(1, 245))
    if user:
        fl = FriendList().get_friends(user=user)
        for u,f in fl.items():
            if len(f)>0:
                friend = f[0]
                break
    return {user: friend}