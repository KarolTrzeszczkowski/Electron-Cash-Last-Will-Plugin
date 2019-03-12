from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import webbrowser
from .last_will_contract import LastWillContract
from electroncash.address import Address, Script, hash160, ScriptOutput, OpCodes
from electroncash.transaction import Transaction,TYPE_ADDRESS, TYPE_SCRIPT
import electroncash.web as web

from electroncash.i18n import _
from electroncash_gui.qt.util import *
from electroncash.wallet import Multisig_Wallet
from electroncash.util import print_error, print_stderr, NotEnoughFunds
from electroncash_gui.qt.transaction_dialog import show_transaction
from .contract_finder import find_contract
from .last_will_contract import LastWillContractManager


class Intro(QDialog, MessageBoxMixin):
    def __init__(self, parent, plugin, wallet_name, address, manager=None):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        self.contract=None
        self.contractTx=None
        self.manager=None
        hbox = QHBoxLayout()
        l = QLabel("<b>%s</b>"%(_("Manage my Last Will:")))
        vbox.addWidget(l)
        vbox.addLayout(hbox)
        b = QPushButton(_("Create new Last Will contract"))
        b.clicked.connect(lambda : switch_to(Creating, self.main_window, self.plugin, self.wallet_name,self.manager))
        hbox.addWidget(b)

        b = QPushButton(_("Find existing Last Will"))
        b.clicked.connect(self.handle_finding)
        hbox.addWidget(b)
        vbox.addStretch(1)

    def handle_finding(self):
        try:
            self.contractTx, self.contract, role = find_contract(self.wallet)
        except:
            print("No contract")
        else:
            if self.wallet.has_password():
                self.main_window.show_error(_("Last Will Contract found! Last Will plugin requires password. It will get access to your private keys."))
                self.password = self.main_window.password_dialog()
                if not self.password:
                    return
            i = self.wallet.get_address_index(self.contract.addresses[role])
            priv = self.wallet.keystore.get_private_key(i, self.password)[0]
            public = self.wallet.get_public_keys(self.contract.addresses[role])
            self.manager = LastWillContractManager(self.contractTx, self.contract, public, priv, role)
            switch_to(Manage,self.main_window, self.plugin, self.wallet_name,self.manager)






class Creating(QDialog, MessageBoxMixin):
    search_done_signal = pyqtSignal(object)


    def __init__(self, parent, plugin, wallet_name, address, manager):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.password=None
        self.contract=None
        if self.wallet.has_password():
            self.main_window.show_error(_("Last Will requires password. It will get access to your private keys."))
            self.password = parent.password_dialog()
            if not self.password:
                return
        self.fund_domain = None
        self.fund_change_address = None
        self.refresh_address = self.wallet.get_unused_address()
        self.inheritor_address=None
        self.cold_address=None
        self.value=0
        index = self.wallet.get_address_index(self.refresh_address)
        key = self.wallet.keystore.get_private_key(index,self.password)
        self.privkey = int.from_bytes(key[0], 'big')

        if isinstance(self.wallet, Multisig_Wallet):
            self.main_window.show_error(
                "Last Will is designed for single signature wallet only right now")

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        l = QLabel("<b>%s</b>" % (_("Creatin Last Will contract:")))
        vbox.addWidget(l)
        l = QLabel(_("Refreshing address") + ": auto (this wallet)") #self.refreshing_address.to_ui_string())
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(l)

        grid = QGridLayout()
        vbox.addLayout(grid)

        l = QLabel(_("Inheritor address: "))
        grid.addWidget(l, 0, 0)

        l = QLabel(_("Value (sats)"))
        grid.addWidget(l, 0, 1)

        self.inheritor_address_wid = QLineEdit()
        self.inheritor_address_wid.textEdited.connect(self.inheritance_info_changed)
        grid.addWidget(self.inheritor_address_wid, 1, 0)

        self.inheritance_value_wid = QLineEdit()
        self.inheritance_value_wid.setMaximumWidth(70)
        self.inheritance_value_wid.setAlignment(Qt.AlignRight)
        self.inheritance_value_wid.textEdited.connect(self.inheritance_info_changed)
        grid.addWidget(self.inheritance_value_wid, 1, 1)
        l = QLabel(_("My cold wallet address: "))
        grid.addWidget(l, 2, 0)
        self.cold_address_wid = QLineEdit()
        self.cold_address_wid.textEdited.connect(self.inheritance_info_changed)
        grid.addWidget(self.cold_address_wid, 3, 0)
        b = QPushButton(_("Create Last Will"))
        b.clicked.connect(lambda: self.create_last_will())
        vbox.addStretch(1)
        vbox.addWidget(b)
        self.create_button = b
        self.create_button.setDisabled(True)
        vbox.addStretch(1)


    def inheritance_info_changed(self, ):
            # if any of the txid/out#/value changes
        try:
            self.inheritor_address = Address.from_string(self.inheritor_address_wid.text())
            self.cold_address = Address.from_string(self.cold_address_wid.text())
            self.value = int(self.inheritance_value_wid.text())
        except:
            self.create_button.setDisabled(True)
        else:
            self.create_button.setDisabled(False)
            addresses = [self.refresh_address, self.cold_address, self.inheritor_address]
            self.contract=LastWillContract(addresses)


    def create_last_will(self, ):
        outputs = [(TYPE_ADDRESS, self.contract.address, self.value),
                   #(TYPE_SCRIPT, ScriptOutput(make_opreturn(self.contract.redeemscript)),0),
                   (TYPE_ADDRESS, self.refresh_address, 546),
                   (TYPE_ADDRESS, self.cold_address, 546),
                   (TYPE_ADDRESS, self.inheritor_address, 546),]

        try:
            tx = self.wallet.mktx(outputs, self.password, self.config,
                                  domain=self.fund_domain, change_addr=self.fund_change_address)
        except NotEnoughFunds:
            return self.show_critical(_("Not enough balance to fund smart contract."))
        except Exception as e:
            return self.show_critical(repr(e))
        tx.version=2
        show_transaction(tx, self.main_window, "Make Last Will contract", prompt_if_unsaved=True)



class Manage(QDialog, MessageBoxMixin):
    search_done_signal = pyqtSignal(object)


    def __init__(self, parent, plugin, wallet_name, address, manager):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.manager=manager
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        if self.manager.mode==0:
            mode="refreshing"
        elif self.manager.mode==1:
            mode="cold"
        elif self.manager.mode==2:
            mode="inheritor"
        l = QLabel("<b>%s</b>" % (_("This is :" + mode)))
        vbox.addWidget(l)



def switch_to(mode, main_window, plugin, wallet_name,manager):
    l = mode(main_window, plugin, wallet_name, address=None,manager=manager)
    tab = main_window.create_list_tab(l)
    i = main_window.tabs.indexOf(plugin.lw_tabs.get(wallet_name, None))

    plugin.lw_tabs[wallet_name] = tab
    plugin.lw_tab[wallet_name] = l
    main_window.tabs.addTab(tab, QIcon(":icons/preferences.png"), _('Last Will'))
    main_window.tabs.removeTab(i)


def make_opreturn(data):
    """Turn data bytes into a single-push opreturn script"""
    if len(data) < 76:
        return bytes((OpCodes.OP_RETURN, len(data))) + data
    elif len(data) < 256:
        return bytes((OpCodes.OP_RETURN, 76, len(data))) + data
    else:
        raise ValueError(data)

