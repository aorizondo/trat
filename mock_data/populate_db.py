#!/usr/bin/python
# -*- coding: utf-8 -*-

from jim.lib import ServerStorage, FriendList, ClientStorage
from jim.app_config import ALLOWED_ACTIONS
import json
import random

# ------------------- SERVER SIDE -------------------

db = ServerStorage()

# # actions
# for act in ALLOWED_ACTIONS:
#     db.add_action(act)
#
# # groups
# with open('groups.json') as json_data:
#     list = json.load(json_data)
#     for i in list:
#         print(i)
#         db.add_group(i['group'])
#
# # users
# with open('users.json') as json_data:
#     list = json.load(json_data)
#     for i in list:
#         print(i)
#         db.add_user(i['login'], i['info'])
#
# # users to groups
# for u in range(1, 250):
#     user = db.get_user_by_id(u)
#
#     if user:
#         g1 = db.get_group_by_id(random.randrange(100))
#         g2 = db.get_group_by_id(random.randrange(100))
#
#     if g1:
#         db.add_to_group(user, g1)
#     if g2:
#         db.add_to_group(user, g2)
#
# # friends
fl = FriendList()
poll = 250
for i in range(1, poll):
    user = db.get_user_by_id(i)
    f1 = db.get_user_by_id(random.randrange(poll))
    f2 = db.get_user_by_id(random.randrange(poll))
    f3 = db.get_user_by_id(random.randrange(poll))
    f4 = db.get_user_by_id(random.randrange(poll))
    f5 = db.get_user_by_id(random.randrange(poll))

    if user:
        try:
            if f1:
                fl.add_friend(user.login, f1.login)
            if f2:
                fl.add_friend(user.login, f2.login)
            if f3:
                fl.add_friend(user.login, f3.login)
            if f4:
                fl.add_friend(user.login, f4.login)
            if f5:
                fl.add_friend(user.login, f5.login)
        except:
            pass

print('OK')