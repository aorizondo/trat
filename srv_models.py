#!/usr/bin/python
# -*- coding: utf-8 -*-

from jim.app_config import SERVER_DB_ENGINE
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, BLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    user_id = Column(Integer, primary_key=True)
    created_date = Column(DateTime, default=func.now())
    login = Column(String(100), unique=True, nullable=False)
    password = Column(String(64), nullable=True)
    info = Column(String(250), nullable=True)
    groups = relationship(
        'Group',
        secondary='group_membership'
    )

    def __init__(self, login, password, info):
        self.login = login
        self.password = password
        if info:
            self.info = info

    def __repr__(self):
        return "<User('{}, '{}')>".format(self.login, self.user_id)


class UserHistory(Base):
    __tablename__ = 'user_history'
    history_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'))
    added_date = Column(DateTime, default=func.now())
    ip_addr = Column(String(15))
    action = Column(Integer, ForeignKey('action.action_id'))

    def __init__(self, user_id, ip_addr, action):
        self.user_id = user_id
        self.ip_addr = ip_addr
        self.action = action

    def __repr__(self):
        return "<UserHistory('{}', '{}')>".format (self.user_id, self.action)


class UserFriend(Base):
    __tablename__ = 'user_friends'
    contact_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'))
    friend_id = Column(Integer, ForeignKey('user.user_id'))
    added_date = Column(DateTime, default=func.now())

    def __init__(self, user_id, friend_id):
        self.user_id = user_id
        self.friend_id = friend_id


class Group(Base):
    __tablename__ = 'group'
    group_id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=True)
    members = relationship(
        'User',
        secondary='group_membership'
    )

    def __init__(self, name):
        self.name = name


class Action(Base):
    __tablename__ = 'action'
    action_id = Column(Integer, primary_key=True)
    name = Column(String(10), nullable=False, unique=True)

    def __init__(self, name):
        self.name = name


class GroupMembership(Base):
    __tablename__ = 'group_membership'
    group_id = Column(Integer, ForeignKey('group.group_id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.user_id'), primary_key=True)

    def __init__(self, user, group):
        self.user_id = user.user_id
        self.group_id = group.group_id


class ServerImages(Base):
    __tablename__= 'server_images'
    id = Column(Integer, primary_key=True)
    image_data = Column(BLOB, nullable=False)
    user_id = Column(Integer, ForeignKey('user.user_id'))
    comment = Column(String(20), nullable=True)

    def __init__(self, image_data, user_id, comment):
        self.image_data = image_data
        self.user_id = user_id
        self.comment = comment


Base.metadata.create_all(SERVER_DB_ENGINE)