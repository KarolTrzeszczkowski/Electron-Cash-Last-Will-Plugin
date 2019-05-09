from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from electroncash.address import Address, ScriptOutput
from .util import make_opreturn
from electroncash.transaction import TYPE_ADDRESS, TYPE_SCRIPT
from electroncash.bitcoin import encrypt_message
import base64
import string
import random

class NotificationWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        vbox = QVBoxLayout(self)
        self.tab=parent
        self.nottify_me_fee = 100000
        self.nottify_inheritor_fee = 1000000
        self.licho_pubkey = "025721bdf418d241dc886faa79dfc3bac58092b1750b8253ad43d38feb00858b44"
        self.licho_address = Address.from_pubkey(self.licho_pubkey)
        hbox = QHBoxLayout()
        l = QLabel("<b> %s </b>" % "Licho Notification Service")
        self.enable_service = QCheckBox()
        self.enable_service.stateChanged.connect(self.flip)
        hbox.addWidget(l)
        hbox.addWidget(self.enable_service)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        self.notify_me = QCheckBox(
            "Remind me about the next refreshing one month before the contract expiry date (1 mBCH)")
        self.my_email = QLineEdit()
        self.my_email.setPlaceholderText("My e-mail")
        self.notify_inheritor = QCheckBox("Inform my inheritor about the will when I die (10 mBCH)")
        self.i_email = QLineEdit()
        self.i_email.setPlaceholderText("Inheritors e-mail")
        self.widgets = [self.notify_me, self.my_email, self.notify_inheritor, self.i_email]
        for w in self.widgets:
            vbox.addWidget(w)
        self.disable(True)
        self.disabled=True

    def do_anything(self):
        return (not self.disabled) and (self.notify_me.isChecked() or self.notify_inheritor.isChecked())


    def disable(self, bool):
        for w in self.widgets:
            w.setDisabled(bool)
        self.disabled = bool

    def flip(self):
        if self.disabled:
            self.disable(False)
        else:
            self.disable(True)

    def notification_outputs(self,contract_address):
        if not self.disabled:
            outputs = []
            fee = 0
            str = random.choice(string.ascii_letters+ string.punctuation + string.digits)+'\'' # salt
            if self.notify_me.isChecked():
                str += self.my_email.text()+'\''
                fee += self.nottify_me_fee

            if self.notify_inheritor.isChecked():

                str += self.i_email.text() + '\'' +contract_address.to_ui_string()
                fee += self.nottify_inheritor_fee
            message = base64.b64decode(encrypt_message(str.encode('utf8'),self.licho_pubkey))[4:]
            print(message)
            outputs.append((TYPE_ADDRESS, self.licho_address, fee))
            outputs.append( (TYPE_SCRIPT, ScriptOutput(make_opreturn(message)), 0) )
            return outputs


