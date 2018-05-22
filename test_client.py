#!/usr/bin/python
# -*- coding: utf-8 -*-

import pytest
from client import *
from jim.app_config import *

# на тесты времени не было. допишу постепенно

@pytest.fixture
def cli():
    cl = Client()
    cl.connect()
    return cl


class TestClient:

    def test_connect(self,cli):
        assert cli._socket is not None

    def test_send(self,cli):
        msg = Message(MSG, 'test server')
        response = cli.send(msg)
        assert response['response'] == OK_CODE

