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


class Intro(QDialog, MessageBoxMixin):
    def __init__(self, parent, plugin, wallet_name, address):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        hbox = QHBoxLayout()
        l = QLabel("<b>%s</b>"%(_("Manage my Last Will:")))
        vbox.addWidget(l)
        vbox.addLayout(hbox)
        b = QPushButton(_("Create new Last Will contract"))
        b.clicked.connect(lambda : switch_to(Creating, self.main_window, self.plugin, self.wallet_name))
        hbox.addWidget(b)

        b = QPushButton(_("Find existing Last Will"))
        #b.clicked.connect()
        hbox.addWidget(b)
        vbox.addStretch(1)

    def find_last_will(self,):
        history = self.wallet.get_history()





class Creating(QDialog, MessageBoxMixin):
    search_done_signal = pyqtSignal(object)


    def __init__(self, parent, plugin, wallet_name, address):
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
        sw = lambda : switch_to(Creating, self.main_window, self.plugin, self.wallet_name)
        key = self.wallet.keystore.get_private_key(index,self.password)
        self.privkey = int.from_bytes(key[0], 'big')

        if isinstance(self.wallet, Multisig_Wallet):
            self.main_window.show_error(
                "Last Will is designed for single signature only right now")

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
            self.contract=LastWillContract(self.privkey, self.refresh_address, self.cold_address, self.inheritor_address)


    def create_last_will(self, ):
        outputs = [(TYPE_ADDRESS, self.contract.address, self.value),
                   (TYPE_SCRIPT, ScriptOutput(make_opreturn(self.contract.redeemscript)),0),
                   (TYPE_ADDRESS, self.inheritor_address, 546),
                   (TYPE_ADDRESS, self.cold_address, 546),]

        try:
            tx = self.wallet.mktx(outputs, self.password, self.config,
                                  domain=self.fund_domain, change_addr=self.fund_change_address)
        except NotEnoughFunds:
            return self.show_critical(_("Not enough balance to fund smart contract."))
        except Exception as e:
            return self.show_critical(repr(e))
        show_transaction(tx, self.main_window,
                         "Make Last Will contract",
                         prompt_if_unsaved=True)


def switch_to(mode, main_window, plugin, wallet_name):
    l = mode(main_window, plugin, wallet_name, address=None)
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



class Manage(QDialog, MessageBoxMixin):
    search_done_signal = pyqtSignal(object)


    def __init__(self, parent, plugin, wallet_name, address):
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


class CreatingOld(QDialog, MessageBoxMixin):
    search_done_signal = pyqtSignal(object)


    def __init__(self, parent, plugin, wallet_name, address):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.password=None
        if self.wallet.has_password():
            self.main_window.show_error(_("Last Will requires password. It will get access to your private keys."))
            self.password = parent.password_dialog()
            if not self.password:
                return

        if address:
            self.fund_domain = [address]
            self.fund_change_address = address
            self.refreshing_address = address
            self.entropy_address = address
        else:
            self.fund_domain = None
            self.fund_change_address = None
            self.refreshing_address = self.wallet.get_unused_address()
            self.entropy_address = self.wallet.get_addresses()[0]
        if not self.refreshing_address:
            # self.wallet.get_unused_address() returns None for imported privkey wallets.
            self.main_window.show_error(_("For imported private key wallets, please open the coin splitter from the Addresses tab by right clicking on an address, instead of via the Tools menu."))
            return

        # Extract private key
        index = self.wallet.get_address_index(self.entropy_address)

        key = self.wallet.keystore.get_private_key(index,self.password)
        privkey = int.from_bytes(key[0], 'big')

        if isinstance(self.wallet, Multisig_Wallet):
            self.main_window.show_error(
                "Last Will is designes for single signature only right now")

        #
        #       TWORZYMY KONTRAKT
        self.refreshing_address=None
        self.cold_address=None
        self.inheritor_address=None

        self.contract = LastWillContract(privkey, self.refreshing_address, self.cold_address, self.inheritor_address)


        self.setWindowTitle(_("Last Will Plugin"))

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        l = QLabel(_("Master address") + ": " + self.entropy_address.to_ui_string())
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(l)

    #    l = QLabel(_("Last Will contract address") + ": " + self.contract.address.to_ui_string())
    #    l.setTextInteractionFlags(Qt.TextSelectableByMouse)
    #    vbox.addWidget(l)

        hbox = QHBoxLayout()
        vbox.addLayout(hbox)


        b = QPushButton(_("View your Last Will contract"))
        b.clicked.connect(self.showscript)
        hbox.addWidget(b)

        hbox.addStretch(1)


        l = QLabel("<b>%s</b>"%(_("Contract finding:")))
        vbox.addWidget(l)

        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        b = QPushButton(_("Create Last Will contract"))
        b.clicked.connect(self.fund)
        hbox.addWidget(b)
        self.fund_button = b

        b = QPushButton("x")
        b.clicked.connect(self.search)
        hbox.addWidget(b)
        self.search_button = b

        hbox.addStretch(1)


        grid = QGridLayout()
        vbox.addLayout(grid)

        l = QLabel(_("TXID"))
        grid.addWidget(l, 0, 0)

        l = QLabel(_("Out#"))
        grid.addWidget(l, 0, 1)

        l = QLabel(_("Value (sats)"))
        grid.addWidget(l, 0, 2)

        self.fund_txid_e = QLineEdit()
        self.fund_txid_e.textEdited.connect(self.changed_coin)
        grid.addWidget(self.fund_txid_e, 1, 0)

        self.fund_txout_e = QLineEdit()
        self.fund_txout_e.setMaximumWidth(40)
        self.fund_txout_e.setAlignment(Qt.AlignRight)
        self.fund_txout_e.textEdited.connect(self.changed_coin)
        grid.addWidget(self.fund_txout_e, 1, 1)

        self.fund_value_e = QLineEdit()
        self.fund_value_e.setMaximumWidth(70)
        self.fund_value_e.setAlignment(Qt.AlignRight)
        self.fund_value_e.textEdited.connect(self.changed_coin)
        grid.addWidget(self.fund_value_e, 1, 2)


        l = QLabel("<b>%s</b>"%(_("Splittable coin spending:")))
        vbox.addWidget(l)

        self.option1_rb = QRadioButton(_("Only spend splittable coin"))
        self.option2_rb = QRadioButton(_(""))
        self.option1_rb.setChecked(True)
        vbox.addWidget(self.option1_rb)

        if self.fund_change_address:
            self.option2_rb.setText(_("Combine with all coins from address") + " %.10s..."%(self.fund_change_address.to_ui_string()))
            self.option2_rb.setChecked(True)
        else:
            self.option2_rb.setHidden(True)


        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        l = QLabel(_("Output to:"))
        hbox.addWidget(l)
        self.redeem_address_e = QLineEdit()
        self.redeem_address_e.setText(self.refreshing_address.to_full_ui_string())
        hbox.addWidget(self.redeem_address_e)


        hbox = QHBoxLayout()
        vbox.addLayout(hbox)

        b = QPushButton(_("Redeem with split (CDS chain only)"))
        b.clicked.connect(lambda: self.spend())
        hbox.addWidget(b)
        self.redeem_button = b


        self.changed_coin()

        self.search_done_signal.connect(self.search_done)
        self.search()

        self.show()

    def showscript(self, ):
        if not self.contract:
            return
        script = self.contract.redeemscript
        schex = script.hex()

        try:
            sco = ScriptOutput(script)
            decompiled = sco.to_ui_string()
        except:
            decompiled = "decompiling error"

        d = QDialog(self)
        d.setWindowTitle(_('Split contract script'))
        d.setMinimumSize(610, 490)

        layout = QGridLayout(d)

        script_bytes_e = QTextEdit()
        layout.addWidget(QLabel(_('Bytes')), 1, 0)
        layout.addWidget(script_bytes_e, 1, 1)
        script_bytes_e.setText(schex)
        script_bytes_e.setReadOnly(True)
        # layout.setRowStretch(2,3)

        decompiled_e = QTextEdit()
        layout.addWidget(QLabel(_('ASM')), 3, 0)
        layout.addWidget(decompiled_e, 3, 1)
        decompiled_e.setText(decompiled)
        decompiled_e.setReadOnly(True)
        # layout.setRowStretch(3,1)

        hbox = QHBoxLayout()

        b = QPushButton(_("Close"))
        b.clicked.connect(d.accept)
        hbox.addWidget(b)

        layout.addLayout(hbox, 4, 1)
        d.show()

    def changed_coin(self, ):
        # if any of the txid/out#/value changes
        try:
            txid = bytes.fromhex(self.fund_txid_e.text())
            assert len(txid) == 32
            prevout_n = int(self.fund_txout_e.text())
            value = int(self.fund_value_e.text())
        except:
            self.redeem_button.setDisabled(True)
        else:
            self.redeem_button.setDisabled(False)


    def fund(self, ):
        outputs = [(TYPE_ADDRESS, self.contract.address, 1000)]
        try:
            tx = self.wallet.mktx(outputs, self.password, self.config,
                                  domain=self.fund_domain, change_addr=self.fund_change_address)
        except NotEnoughFunds:
            return self.show_critical(_("Not enough balance to fund smart contract."))
        except Exception as e:
            return self.show_critical(repr(e))
        for i, out in enumerate(tx.outputs()):
            if out[1] == self.contract.address:
                self.fund_txout_e.setText(str(i))
                self.fund_value_e.setText(str(out[2]))
                break
        else:
            raise RuntimeError("Created tx is incorrect!")
        self.fund_txid_e.setText(tx.txid())
        self.fund_txid_e.setCursorPosition(0)
        show_transaction(tx, self.main_window,
                         "Make contract",
                         prompt_if_unsaved=True)
        self.changed_coin()

    def spend(self):
        prevout_hash = self.fund_txid_e.text()
        prevout_n = int(self.fund_txout_e.text())
        value = int(self.fund_value_e.text())
        locktime = self.contract.seconds
        estimate_fee = lambda x: (1 * x)
        out_addr = Address.from_string(self.redeem_address_e.text())

        # generate the special spend
        inp = self.contract.makeinput(prevout_hash, prevout_n, value)

        inputs = [inp]
        invalue = value

        # add on other spends
        if self.option1_rb.isChecked():
            domain = []
        else:
            raise RuntimeError

        outputs = [(TYPE_ADDRESS, out_addr, 0)]
        tx1 = Transaction.from_io(inputs, outputs, locktime)
        txsize = len(tx1.serialize(True)) // 2
        fee = estimate_fee(txsize)

        outputs = [(TYPE_ADDRESS, out_addr, invalue - fee)]
        tx = Transaction.from_io(inputs, outputs, locktime)
        self.contract.signtx(tx)
        self.wallet.sign_transaction(tx, self.password)
        self.contract.completetx(tx)


        desc = "Spend splittable coin (CDS chain only!)"
        show_transaction(tx, self.main_window,
                         desc,
                         prompt_if_unsaved=True)

    def search(self, ):
        self.search_button.setIcon(QIcon(":icons/status_waiting"))
        self.search_button.setText(_("Searching..."))
        self.search_button.setDisabled(True)

        self.wallet.network.send([("blockchain.scripthash.listunspent",
                                   [self.contract.address.to_scripthash_hex()]),
                                  ],
                                 self.search_done_signal.emit)

    def search_done(self, response):
        error = response.get('error')
        result = response.get('result')
        params = response.get('params')

        if result and not error:
            # just grab first utxo
            utxo = result[0]
            self.fund_txid_e.setText(utxo['tx_hash'])
            self.fund_txid_e.setCursorPosition(0)
            self.fund_txout_e.setText(str(utxo['tx_pos']))
            self.fund_value_e.setText(str(utxo['value']))
            self.changed_coin()
            self.search_button.setIcon(QIcon(":icons/tab_coins"))
            self.search_button.setText(_("Found splittable coin!"))
            self.search_button.setDisabled(True)
            self.fund_button.setDisabled(True)
            return

        if error:
            self.show_error("Search request error: " + str(error))

        self.search_button.setIcon(QIcon())
        self.search_button.setText(_("Find splittable coin"))
        self.search_button.setDisabled(False)
    def create_menu(self):
        pass

    def on_delete(self):
        pass

    def on_update(self):
        pass

