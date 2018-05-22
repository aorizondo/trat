#!/usr/bin/python
# -*- coding: utf-8 -*-

from jim.app_config import CLIENT_DB_ENGINE
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, BLOB, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LocalUser(Base):
    __tablename__ = 'local_users'
    row_id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    login = Column(String(100), nullable=False)

    def __init__(self, user_id, login, owner_id):
        if user_id:
            self.user_id = user_id
        self.login = login
        self.owner_id = owner_id

    def __repr__(self):
        return "<LocalUser('{}, {}')>".format(self.login, self.user_id)


class NonVerifiedContacts(Base):
    __tablename__ = 'non_verified_contacts'
    user_id = Column(Integer, primary_key=True)
    login = Column(String(100), unique=True, nullable=False)

    def __init__(self, login):
        self.login = login


class ClientFriends(Base):
    __tablename__ = 'client_friends'
    contact_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('local_users.user_id'))
    friend_id = Column(Integer, ForeignKey('local_users.user_id'))

    def __init__(self, user_id, friend_id):
        self.user_id = user_id
        self.friend_id = friend_id


class ClientMessages(Base):
    __tablename__ = 'client_messages'
    message_id = Column(Integer, primary_key=True)
    message = Column(String(500))
    user_id = Column(Integer, ForeignKey('local_users.user_id'), nullable=False)
    friend_id = Column(Integer, ForeignKey('local_users.user_id'), nullable=True)
    added_date = Column(DateTime, default=func.now())
    incoming = Column(Boolean, default=False)

    def __init__(self, user_id, friend_id=None, message='', incoming=False):
        self.user_id = user_id
        if bool(friend_id):
            self.friend_id = friend_id
        self.message = message
        self.incoming = incoming


class LocalImages(Base):
    __tablename__= 'local_images'
    id = Column(Integer, primary_key=True)
    image_data = Column(BLOB, nullable=False)
    user_id = Column(Integer, ForeignKey('local_users.user_id'))
    comment = Column(String(20), nullable=True)

    def __init__(self, image_data, user_id, comment):
        self.image_data = image_data
        self.user_id = user_id
        self.comment = comment




Base.metadata.create_all(CLIENT_DB_ENGINE)