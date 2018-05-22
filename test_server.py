#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
from server import *
from client import *
from jim.app_config import *

# на тесты времени не было. допишу постепенно


class TestServer:

    def test_start(self):
        srv = Server()
        assert srv.start() == True

    def test_check_msg(self):
        pass

