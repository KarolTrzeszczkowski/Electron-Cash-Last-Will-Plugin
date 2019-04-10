from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import webbrowser
from .last_will_contract import LastWillContract
from electroncash.address import ScriptOutput
from electroncash.transaction import Transaction,TYPE_ADDRESS, TYPE_SCRIPT
import electroncash.web as web

from electroncash.i18n import _
from electroncash_gui.qt.util import *
from electroncash.wallet import Multisig_Wallet
from electroncash.util import NotEnoughFunds
from electroncash_gui.qt.transaction_dialog import show_transaction
from .contract_finder import find_contract, extract_contract_data
from .last_will_contract import LastWillContractManager
from .notification_service import NotificationWidget
from .util import *
import time, json
from math import ceil



class Intro(QDialog, MessageBoxMixin):

    def __init__(self, parent, plugin, wallet_name, password, manager=None):
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
        self.password = None
        self.role=0
        hbox = QHBoxLayout()
        if is_expired():
            l = QLabel(_("Please update your plugin"))
            l.setStyleSheet("QLabel {color:#ff0000}")
            vbox.addWidget(l)
        l = QLabel("<b>%s</b>"%(_("Manage my Last Will:")))
        vbox.addWidget(l)
        vbox.addLayout(hbox)
        b = QPushButton(_("Create new Last Will contract"))
        b.clicked.connect(lambda : switch_to(Create, self.main_window, self.plugin, self.wallet_name, None, self.manager))
        hbox.addWidget(b)
        b = QPushButton(_("Find existing Last Will contract"))
        b.clicked.connect(self.handle_finding)
        hbox.addWidget(b)
        b = QPushButton(_("Load Last Will contract info"))
        b.clicked.connect(self.load)
        hbox.addWidget(b)
        vbox.addStretch(1)

    def handle_finding(self):
        print(find_contract(self.wallet))
        try:
            self.contractTx, self.contract, self.role = find_contract(self.wallet)[0] # grab first contract, multicontract support later
        except:
            print("No contract")
        else:
            self.start_manager()

    def load(self):
        fileName = self.main_window.getOpenFileName("Load Last Will Contract Info", "*.json")
        try:
            with open(fileName, "r") as f:
                file_content = f.read()
        except:
            return
        data = json.loads(file_content)
        try:
            self.contract = extract_contract_data(data.get("initial_tx"))
            self.contractTx = [data.get("utxo")]
            self.role = data.get('role')
            assert role == 1
        except:
            print("No contract or wrong wallet")
            return
        else:
            self.start_manager()

    def start_manager(self):
        if self.wallet.has_password():
            self.main_window.show_error(_(
                "Last Will Contract found! Last Will plugin requires password. It will get access to your private keys."))
            self.password = self.main_window.password_dialog()
            if not self.password:
                return
        i = self.wallet.get_address_index(self.contract.addresses[self.role])
        if not self.wallet.is_watching_only():
            priv = self.wallet.keystore.get_private_key(i, self.password)[0]
        else:
            print("watch only")
            priv = None
        try:
            public = self.wallet.get_public_keys(self.contract.addresses[self.role])
        except:
            self.show_error("Wrong wallet.")
        self.manager = LastWillContractManager(self.contractTx, self.contract, public, priv, self.role)
        switch_to(Manage, self.main_window, self.plugin, self.wallet_name, self.password, self.manager)






class Create(QDialog, MessageBoxMixin):

    def __init__(self, parent, plugin, wallet_name, password, manager):
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
        self.inheritance_value_wid.setMaximumWidth(100)
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
        self.notification = NotificationWidget(self)
        vbox.addWidget(self.notification)
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

        outputs = [(TYPE_SCRIPT, ScriptOutput(make_opreturn(self.contract.address.to_ui_string().encode('utf8'))),0),
                   (TYPE_ADDRESS, self.refresh_address, self.value+190),
                   (TYPE_ADDRESS, self.cold_address, 546),
                   (TYPE_ADDRESS, self.inheritor_address, 546)]
        try:
            tx = self.wallet.mktx(outputs, self.password, self.config,
                                  domain=self.fund_domain, change_addr=self.fund_change_address)
            id = tx.txid()
        except NotEnoughFunds:
            return self.show_critical(_("Not enough balance to fund smart contract."))
        except Exception as e:
            return self.show_critical(repr(e))

        # preparing transaction, contract can't give a change
        self.main_window.network.broadcast_transaction2(tx)
        self.create_button.setText("Creating Last Will...")
        self.create_button.setDisabled(True)
        coin = self.wait_for_coin(id,10)
        self.wallet.add_input_info(coin)
        inputs = [coin]
        outputs = [(TYPE_ADDRESS, self.contract.address, self.value)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version=2
        show_transaction(tx, self.main_window, "Make Last Will contract", prompt_if_unsaved=True)

        if self.notification.do_anything() :
            outputs = self.notification.notification_outputs(self.contract.address)
            tx = self.wallet.mktx(outputs, self.password, self.config,
                              domain=self.fund_domain, change_addr=self.fund_change_address)
            show_transaction(tx, self.main_window, "Notification service payment", prompt_if_unsaved=True)

        switch_to(Intro, self.main_window, self.plugin, self.wallet_name, None, None)


    def wait_for_coin(self, id, timeout=10):
        for j in range(timeout):
            coins = self.wallet.get_spendable_coins(None, self.config)
            for c in coins:
                if c.get('prevout_hash') == id:
                    if c.get('value')==self.value+190:
                        return c
            time.sleep(1)
            print("Waiting for coin: "+str(j)+"s")
        return None



class Manage(QDialog, MessageBoxMixin):
    def __init__(self, parent, plugin, wallet_name, password, manager):
        QDialog.__init__(self, parent)

        self.password=password

        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.manager=manager
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        self.fee=1000

        self.mode_label = QLabel()
        vbox.addWidget(self.mode_label)
        l = QLabel(_("Value :" + str(self.manager.tx.get("value"))))
        vbox.addWidget(l)
        label = self.estimate_expiration()
        l= QLabel(label)
        vbox.addWidget(l)

        if self.manager.mode==0:
            label = self.refresh_lock()
            l = QLabel(label)
            vbox.addWidget(l)
            self.mode_label.setText(_("<b>%s</b>" % (_("This is refreshing wallet."))))
            b = QPushButton(_("Refresh"))
            b.clicked.connect(self.refresh)
            self.notification = NotificationWidget(self)
            vbox.addWidget(self.notification)
            vbox.addStretch(1)
            vbox.addWidget(b)
        elif self.manager.mode==1:
            self.mode_label.setText(_("<b>%s</b>" % (_("This is cold wallet."))))
            b = QPushButton(_("Export contract info"))
            b.clicked.connect(self.export)
            vbox.addWidget(b)
            b = QPushButton(_("End contract"))
            b.clicked.connect(self.end)
            vbox.addWidget(b)
        else:
            self.mode_label.setText(_("<b>%s</b>" % (_("This is inheritors wallet."))))
            b = QPushButton(_("Inherit"))
            b.clicked.connect(self.end)
            vbox.addWidget(b)



    def end(self):
        inputs = [self.manager.txin]
        outputs = [(TYPE_ADDRESS, self.manager.contract.addresses[self.manager.mode], self.manager.value - self.fee)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version=2
        if not self.wallet.is_watching_only():
            self.manager.signtx(tx)
            self.manager.completetx(tx)
        show_transaction(tx, self.main_window, "End Last Will contract", prompt_if_unsaved=True)
        switch_to(Intro, self.main_window, self.plugin, self.wallet_name, None, None)

    def refresh(self):
        if self.manager.mode!=0:
            print("This wallet can't refresh a contract!")
            return
        print("Notification Service: ")
        print(self.notification.do_anything())
        if self.notification.do_anything() :
            outputs = self.notification.notification_outputs(self.manager.contract.address)
            tx = self.wallet.mktx(outputs, self.password, self.config, None, None)
            show_transaction(tx, self.main_window, "Notification service payment", prompt_if_unsaved=True)

        inputs = [self.manager.txin]
        outputs = [(TYPE_ADDRESS, self.manager.contract.address, self.manager.value-self.fee)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        self.manager.signtx(tx)
        self.wallet.sign_transaction(tx, self.password)
        self.manager.completetx_ref(tx)
        show_transaction(tx, self.main_window, "Refresh Last Will contract", prompt_if_unsaved=True)


        switch_to(Intro, self.main_window,self.plugin, self.wallet_name,None,None)

    def get_age(self):
        txHeight = self.manager.tx.get("height")
        currentHeight=self.main_window.network.get_local_height()
        age = ceil((currentHeight-txHeight)/144)
        return age

    def refresh_lock(self):
        """Contract can be refreshed only when it's one week old"""
        txHeight = self.manager.tx.get("height")
        age = self.get_age()
        print("Age: " +str(age) + " Height: "+str(txHeight))
        if txHeight==0 :
            label = _("Refresh lock: " + str(7) + " days")
        elif (7-age) > 0:
            label = _("Refresh lock:" + str(8-age) + " days" )
        else :
            label = _("You can refresh your contract.")
        return label

    def estimate_expiration(self):
        """estimates age of the utxo in days. There are 144 blocks per day on average"""
        txHeight = self.manager.tx.get("height")
        age = self.get_age()
        print("Age: " +str(age) + " Height: "+str(txHeight))
        if txHeight==0 :
            label = _("Waiting for confirmation.")
        elif (180-age) > 0:
            label = _("Contract expires in:" +str(180-age)+ " days"  )
        else :
            label = _("Last Will is ready to be inherited.")
        return label

    def export(self):
        name = "Last_Will_Contract_Info_"+ time.strftime("%b%d%Y",time.localtime(time.time())) +".json"
        fileName = self.main_window.getSaveFileName(_("Select where to save your contract info"), name, "*.txn")
        t = find_contract(self.wallet, 'local')[0]
        mycontract = {'utxo' : self.manager.tx, 'initial_tx' : t, 'role':self.manager.mode}
        if fileName:
            with open(fileName, "w+") as f:
                j = json.dumps(mycontract, indent=4)
                f.write(j)
            self.show_message(_("Contract info saved successfully."))






def switch_to(mode, main_window, plugin, wallet_name,password,manager):
    l = mode(main_window, plugin, wallet_name, password=password, manager=manager)
    tab = main_window.create_list_tab(l)
    i = main_window.tabs.indexOf(plugin.lw_tabs.get(wallet_name, None))

    plugin.lw_tabs[wallet_name] = tab
    plugin.lw_tab[wallet_name] = l
    main_window.tabs.addTab(tab, QIcon(":icons/preferences.png"), _('Last Will'))
    main_window.tabs.removeTab(i)




