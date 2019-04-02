from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class NotificationWidget(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        vbox = QVBoxLayout(self)
        self.tab=parent
        l = QLabel("<b> %s </b>" % "Licho Notification Service")
        vbox.addWidget(l)
        self.nottify_me = QCheckBox(
            "Remind me about the next refreshing one week before the contract expiry date (1 mBCH) (Coming soon)")
        self.my_email = QLineEdit()
        self.my_email.setPlaceholderText("My e-mail")
        self.nottify_inheritor = QCheckBox("Inform my inheritor about the will when I die (10 mBCH) (Coming soon)")
        self.i_email = QLineEdit()
        self.i_email.setPlaceholderText("Inheritors e-mail")
        notification_service = [self.nottify_me, self.my_email, self.nottify_inheritor, self.i_email]
        [vbox.addWidget(w) for w in notification_service]
        # [w.setDisabled(True) for w in notification_service]