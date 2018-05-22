#!/usr/bin/python
# -*- coding: utf-8 -*-


# storage ops
class LoginDoesNotExist(Exception):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Contact {} does not exist'.format(self.name)


# class uses
class BaseClsUsing(Exception):
    def __init__(self, instr, clsname):
        self.clsname = clsname
        self.instr = instr


class IllegalCall(BaseClsUsing):
    def __str__(self):
        return '<{}> - illegal call in <{}> class'.format(self.instr, self.clsname)


class MissedMandatoryUsing(BaseClsUsing):
    def __str__(self):
        return '<{}> using is mandatory in <{}> class'.format(self.instr, self.clsname)