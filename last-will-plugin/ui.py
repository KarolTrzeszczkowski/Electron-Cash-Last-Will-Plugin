from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import webbrowser
from .last_will_contract import LastWillContract
from electroncash.address import Address, Script, hash160, ScriptOutput
from electroncash.transaction import Transaction,TYPE_ADDRESS
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
        b.clicked.connect(lambda : self.switch_to(Creating))
        hbox.addWidget(b)

        b = QPushButton(_("Bump existing Last Will contract"))
        #b.clicked.connect()
        hbox.addWidget(b)
        l = QLabel("<b>%s</b>"%(_("Claim money:")))
        vbox.addWidget(l)
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        b = QPushButton(_("End my contract"))
        hbox.addWidget(b)
        b = QPushButton(_("Receive Inheritance"))
        hbox.addWidget(b)
        vbox.addStretch(1)


    def switch_to(self,mode):
        l = mode(self.main_window, self.plugin, self.wallet_name, address=None)
        tab = self.main_window.create_list_tab(l)
        i=self.main_window.tabs.indexOf(self.plugin.lw_tabs.get(self.wallet_name,None))

        self.plugin.lw_tabs[self.wallet_name] = tab
        self.plugin.lw_tab[self.wallet_name] = l
        self.main_window.tabs.addTab(tab, QIcon(":icons/preferences.png"), _('Last Will2'))
        self.main_window.tabs.removeTab(i)






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
        if self.wallet.has_password():
            self.main_window.show_error(_("Last Will requires password. It will get access to your private keys."))
            self.password = parent.password_dialog()
            if not self.password:
                return

        if address:
            self.fund_domain = [address]
            self.fund_change_address = address
            self.bumping_address = address
            self.entropy_address = address
        else:
            self.fund_domain = None
            self.fund_change_address = None
            self.bumping_address = self.wallet.get_unused_address()
            self.entropy_address = self.wallet.get_addresses()[0]
        if not self.bumping_address:
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
        #

        self.contract = LastWillContract(privkey)


        self.setWindowTitle(_("Last Will Plugin"))

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        l = QLabel(_("Master address") + ": " + self.entropy_address.to_ui_string())
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(l)

        l = QLabel(_("Last Will contract address") + ": " + self.contract.address.to_ui_string())
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(l)

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
        self.redeem_address_e.setText(self.bumping_address.to_full_ui_string())
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