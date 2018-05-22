#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import os

LOG_FOLDER_PATH = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(LOG_FOLDER_PATH, 'client.log')

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    level=logging.DEBUG
)

client_logger = logging.getLogger('client')