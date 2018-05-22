#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import logging.handlers
import os

LOG_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(LOG_FOLDER_PATH, 'server.log')

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    level=logging.DEBUG
)
server_logger = logging.getLogger('server')
server_handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE_PATH, when='d')
server_logger.addHandler(server_handler)