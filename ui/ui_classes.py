#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, re
from PIL import Image as Image
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTimer, QRegExp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QTextCharFormat, QBrush, QColor, QTextCursor
from jim.lib import ClientStorage, ServerStorage, Message, FriendList, FtpClient
from jim.app_config import *
from bs4 import BeautifulSoup
from shutil import copyfile


class ChatDesktopGUI:

    def __init__(self, cli):
        self.ui_dir = os.path.dirname(os.path.abspath(__file__))
        self.cli_app = QtWidgets.QApplication(sys.argv)
        self.server_side = cli is None

        if cli:
            self.client = cli
            self.db = ClientStorage(server_side=False)
            self.friendlist = FriendList()
            self.selected_friend_login = ''
            self.selected_friend = None
            self.timer = QTimer()

            self.mainForm = uic.loadUi(os.path.join(self.ui_dir, 'cli_main.ui'))
            self.mainForm.setFixedSize(self.mainForm.size())
            self.mainForm.textEditChat.setReadOnly(True)

            self.msg_input = self.mainForm.textEditMessageInput
            self.mainForm.textEditSearch.textChanged.connect(self.find_and_highlight_chat_text)

            self.mainForm.listWidgetContacts.itemDoubleClicked.connect(self.set_chat_with)
            self.mainForm.pushButtonAddContact.pressed.connect(self.add_item_to_contact_list)
            self.mainForm.pbSend.pressed.connect(self.send_message)
            self.mainForm.pushButtonAuth.pressed.connect(self.send_auth_request)

            self.avatar = self.mainForm.toolButtonAvatar
            self.avatar.clicked.connect(self.upload_avatar_image)

            self.mainForm.toolButtonItalic.clicked.connect(lambda: self.txt_entag_selected(tag='i'))
            self.mainForm.toolButtonBold.clicked.connect(lambda: self.txt_entag_selected(tag='strong'))
            self.mainForm.toolButtonUnderlined.clicked.connect(lambda: self.txt_entag_selected(tag='u'))
            self.mainForm.toolButtonReset.clicked.connect(lambda: self.txt_entag_selected(tag=''))
            self.mainForm.toolButtonSad.clicked.connect(lambda: self.insert_smile('sad'))
            self.mainForm.toolButtonHappy.clicked.connect(lambda: self.insert_smile('happy'))
            self.mainForm.toolButtonAngry.clicked.connect(lambda: self.insert_smile('angry'))

        else:
            self.db = ServerStorage()
            self.adminForm = uic.loadUi(os.path.join(self.ui_dir, 'srv_admin.ui'))
            self.adminForm.pushButtonRefresh.pressed.connect(self.refresh_srv_connect_list)

    def find_and_highlight_chat_text(self):
        search = self.mainForm.textEditSearch
        chat = self.mainForm.textEditChat
        cursor = chat.textCursor()
        # highlight style
        style = QTextCharFormat()
        style.setBackground(QBrush(QColor(PETER_RIVER)))

        self.set_chat_with()
        pattern = search.toPlainText()
        if bool(pattern):
            try:
                regex = QRegExp(pattern)
                pos = 0
                index = regex.indexIn(chat.toPlainText(), pos)
                while index != -1:
                    # select text and apply the style
                    cursor.setPosition(index)
                    cursor.movePosition(QTextCursor.EndOfWord, 1)
                    cursor.mergeCharFormat(style)
                    # to next matching
                    pos = index + regex.matchedLength()
                    index = regex.indexIn(chat.toPlainText(), pos)
            except Exception:
                pass

    def check_incoming_messages(self):
        if len(self.client.new_messages_arrived_from) > 0:
            self.set_chat_with()

    def set_profile_image(self):
        if not self.server_side:
            if os.path.exists(AVATAR_PATH):
                os.remove(AVATAR_PATH)
            self.db.extract_user_avatar(self.client.user)
            if os.path.exists(AVATAR_PATH):
                img_path = AVATAR_PATH
            else:
                img_path = DEFAULT_AVATAR_PATH
        if bool(img_path):
            self.avatar.setStyleSheet("background-image: url('{}'); border: none;  background-repeat: no-repeat; background-position: center; ".format(img_path))

    def upload_avatar_image(self):
        uploaded = QFileDialog().getOpenFileName(None, "Upload image", "", "JPG-images (*.jpg)")
        if uploaded:
            img_path = uploaded[0]
            if bool(img_path):
                copyfile(img_path, AVATAR_PATH)
                if os.path.exists(AVATAR_PATH):
                    if self.image_resize(AVATAR_PATH, (41, 41)):
                        this_user = self.client.user
                        self.db.del_user_avatars(this_user)
                        self.db.save_image_to_db(AVATAR_PATH, this_user, PROFILE_IMAGE)
                        self.set_profile_image()
                        # upload avatar to ftp
                        ftp = FtpClient()
                        ftp.uploadFile(AVATAR_PATH, this_user.login)
                    else:
                        self.set_profile_image()

    def txt_entag_selected(self, tag=''):
        template = '<{}>{}</{}>' if bool(tag) else '{}{}{}'
        self.msg_input.textCursor().insertHtml(template.format(tag, self.msg_input.textCursor().selectedText(), tag))

    def insert_smile(self, smile):
        smile_path = os.path.join(ICONS_DIR, '{}.png'.format(smile))
        if bool(smile_path):
            if os.path.exists(smile_path):
                self.msg_input.textCursor().insertHtml('<img src="{}" />'.format(smile_path))

    @staticmethod
    def image_resize(img_path, maxsize):
        try:
            im = Image.open(img_path)
            im.thumbnail(maxsize, Image.ANTIALIAS)
            im.save(img_path, 'JPEG')
            return True
        except IOError:
            print('Cannot resize your image!')
            return False

    @staticmethod
    def convert_qt_tags(markup):
        soup = BeautifulSoup(markup, "html.parser")
        if soup.body:
            u_tag = soup.new_tag('u')
            i_tag = soup.new_tag('i')
            strong_tag = soup.new_tag('strong')
            par = soup.body.p
            if par:
                for elm in par.find_all('span', style=re.compile(r"text-decoration: underline;")):
                    u_tag.string = elm.text
                    elm.replace_with(u_tag)
                for elm in par.find_all('span', style=re.compile(r"font-weight:")):
                    strong_tag.string = elm.text
                    elm.replace_with(strong_tag)
                for elm in par.find_all('span', style=re.compile(r"font-style:italic;")):
                    i_tag.string = elm.text
                    elm.replace_with(i_tag)

                # transcode graphic smilies with text, so as not to store paths in db
                images = soup.findAll('img')
                for image in images:
                    text_smile = SMILES_ENCODER[os.path.basename(image['src'])]
                    if bool(text_smile):
                        image.replace_with(text_smile)

                del par['style']
                cleaned = str(par).replace('<p>', '')
                cleaned = cleaned.replace('</p>', '')

                return cleaned
        return markup

    def show_main_form(self, title=None):
        form = self.mainForm if not self.server_side else self.adminForm
        if bool(title):
            form.setWindowTitle(title)
        if form:
            form.show()

    def add_item_to_contact_list(self):
        entered_login = self.mainForm.lineEditAddContact.text().strip()
        if bool(entered_login):
            friend = self.db.add_non_verified(entered_login)
            self.mainForm.listWidgetContacts.addItem(entered_login)
            self.mainForm.lineEditAddContact.clear()
            self.client.send(Message(ADD_CONTACT, None, self.client.user, friend))
            self.client.updated = False
        else:
            self.load_contact_list()

    def set_chat_with(self):

        ui = self.mainForm
        selected_item = ui.listWidgetContacts.currentItem()
        if selected_item:
            self.selected_friend_login = selected_item.text()
            self.selected_friend = self.db.get_user_by_login(self.selected_friend_login)
            te = ui.textEditChat
            te.clear()

            if self.selected_friend_login in self.client.new_messages_arrived_from:
                self.client.new_messages_arrived_from.remove(self.selected_friend_login)

            if self.selected_friend or self.selected_friend_login == COMMON_CHAT:
                html = '<h1>Common chat</h1><hr>' if self.selected_friend_login == COMMON_CHAT \
                    else ('<h1>Chat with: {}</h1><hr>'.format(self.selected_friend_login))
                selected_friend = self.selected_friend if self.selected_friend_login != COMMON_CHAT else None
                messages = self.db.get_local_messages(self.client.user, selected_friend)

                for i in messages:
                    msg_text = self.decode_smiles(i[MESSAGE])
                    html += ('{}  <strong>{}</strong>:<br> {}<br><br>'.format(i[DATE], i[USER_LOGIN].upper(), msg_text))
                te.append(html)

    @staticmethod
    def decode_smiles(source):
        for text_smile, image_name in SMILES_DECODER.items():
            smile_path = os.path.join(ICONS_DIR, image_name)
            source = source.replace(text_smile, '<img src="{}" />'.format(smile_path))
        return source

    def load_contact_list(self, friend_list=None):
        mf = self.mainForm.listWidgetContacts
        mf.clear()

        mf.addItem(COMMON_CHAT)

        if friend_list is None:
            friend_list = self.client.friend_list_request()
        if friend_list:
            if DATA in friend_list:
                data = friend_list[DATA]
                if data:
                    for f in data:
                        mf.addItem(f[FRIEND_LOGIN])

    def send_message(self):
        mi = self.msg_input
        if bool(mi.toPlainText()):
            message_html = mi.toHtml()
            if self.selected_friend or self.selected_friend_login == COMMON_CHAT:
                message_html = self.convert_qt_tags(message_html)
                if self.selected_friend_login == COMMON_CHAT:
                    msg = Message(BROADCAST, message_html, self.client.user)
                else:
                    msg = Message(MSG, message_html, self.client.user, self.selected_friend)
                if self.client.send(msg):
                    self.client.db.store_message(msg)
                mi.clear()
                self.set_chat_with()

    def send_auth_request(self):
        login = self.mainForm.lineEditLogin.text().strip()
        password = self.mainForm.lineEditPass.text().strip()
        if bool(login) and bool(password):
            user = self.db.get_user_by_login(login)
            if user:
                self.client.user = user
                self.client.auth_request(password)
                if self.client.authenticated:
                    print('GUI AUTH OK')
                    self.mainForm.setWindowTitle('{} v.{} : {}'.format(APP_NAME, APP_VERSION, self.client.user.login))
                    # todo: BUG!!! Contact list is sometimes loaded one time at a time.
                    if not self.client.updated:
                        remote_friend_list = self.client.sync_remote_contacts()
                        self.load_contact_list(remote_friend_list)
                    self.main_screen_show()

    def start_app(self):
        sys.exit(self.cli_app.exec_())

    def refresh_srv_connect_list(self):
        cl = self.adminForm.listWidgetConnects
        cl.clear()
        clients = self.db.get_all_users()
        for i in clients:
            cl.addItem('{}, id={}'.format(i.login, i.user_id))

    def set_color_scheme(self, scheme_name):
        if scheme_name == 'night':
            self.mainForm.setStyleSheet("background-color: {}; color: {};  font-weight: normal;".format(MIDNIGHT_BLUE, CLOUDS))
            self.mainForm.groupBoxAuth.setStyleSheet("font-weight: bold;")

            self.mainForm.listWidgetContacts.setStyleSheet("background-color: {}; font-weight: bold;".format(WET_ASPHALT))
            self.mainForm.textEditMessageInput.setStyleSheet("background-color: {};".format(WET_ASPHALT))
            self.mainForm.textEditChat.setStyleSheet("background-color: {};".format(MIDNIGHT_BLUE))

            self.mainForm.lineEditLogin.setStyleSheet("background-color: {}; color: {};".format(CLOUDS, MIDNIGHT_BLUE))
            self.mainForm.lineEditPass.setStyleSheet("background-color: {}; color: {};".format(CLOUDS, MIDNIGHT_BLUE))

            self.mainForm.pushButtonAuth.setStyleSheet("background-color: {};".format(POMEGRANTE))
            self.mainForm.pbSend.setStyleSheet("background-color: {};".format(POMEGRANTE))

    def auth_screen_show(self):
        self.set_color_scheme('night')
        self.mainForm.groupBoxMain.hide()
        self.mainForm.groupBoxAuth.show()

    def main_screen_show(self):
        self.set_profile_image()
        self.mainForm.groupBoxMain.show()
        self.mainForm.groupBoxAuth.hide()
        self.set_messages_window_refresher()

    def set_messages_window_refresher(self):
        self.timer.timeout.connect(self.check_incoming_messages)
        self.timer.start(1000)

    def stop_messages_window_refresher(self):
        self.timer.stop()




