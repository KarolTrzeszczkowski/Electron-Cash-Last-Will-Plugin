from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import electroncash.version
from electroncash.i18n import _
from electroncash.plugins import BasePlugin, hook


class Plugin(BasePlugin):
    electrumcash_qt_gui = None
    # There's no real user-friendly way to enforce this.  So for now, we just calculate it, and ignore it.
    is_version_compatible = True

    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)
        self.network=None
        self.wallet_windows = {}
        self.lw_tabs = {}
        self.lw_tab = {}
    def fullname(self):
        return 'Last Will'

    def description(self):
        return _("Plugin Last Will")

    def is_available(self):
        if self.is_version_compatible is None:
            version = float(electroncash.version.PACKAGE_VERSION)
            self.is_version_compatible = version >= MINIMUM_ELECTRON_CASH_VERSION
        return True


    def on_close(self):
        """
        BasePlugin callback called when the wallet is disabled among other things.
        """
        for window in list(self.wallet_windows.values()):
            self.close_wallet(window.wallet)

    @hook
    def update_contact(self, address, new_entry, old_entry):
        print("update_contact", address, new_entry, old_entry)

    @hook
    def delete_contacts(self, contact_entries):
        print("delete_contacts", contact_entries)

    @hook
    def init_qt(self, qt_gui):
        """
        Hook called when a plugin is loaded (or enabled).
        """
        self.electrumcash_qt_gui = qt_gui
        # We get this multiple times.  Only handle it once, if unhandled.
        if len(self.wallet_windows):
            return
        # These are per-wallet windows.
        for window in self.electrumcash_qt_gui.windows:
            self.load_wallet(window.wallet, window)

    @hook
    def load_wallet(self, wallet, window):
        """
        Hook called when a wallet is loaded and a window opened for it.
        """
        wallet_name = window.wallet.basename()
        self.wallet_windows[wallet_name] = window
        self.add_ui_for_wallet(wallet_name, window)
        self.refresh_ui_for_wallet(wallet_name)


    @hook
    def close_wallet(self, wallet):

        wallet_name = wallet.basename()
        window = self.wallet_windows[wallet_name]
        del self.wallet_windows[wallet_name]
        self.remove_ui_for_wallet(wallet_name, window)


    def add_ui_for_wallet(self, wallet_name, window):
        from .ui import Intro
        l = Intro(window, self, wallet_name, password=None,manager=None)
        tab = window.create_list_tab(l)
        self.lw_tabs[wallet_name] = tab
        self.lw_tab[wallet_name] = l
        window.tabs.addTab(tab, QIcon(":icons/preferences.png"), _('Last Will'))

    def remove_ui_for_wallet(self, wallet_name, window):
        wallet_tab = self.lw_tabs.get(wallet_name, None)
        if wallet_tab is not None:
            del self.lw_tab[wallet_name]
            del self.lw_tabs[wallet_name]
            i = window.tabs.indexOf(wallet_tab)
            window.tabs.removeTab(i)


    def refresh_ui_for_wallet(self, wallet_name):
        wallet_tab = self.lw_tabs[wallet_name]
        wallet_tab.update()

    def switch_to(self, mode, wallet_name, password, manager):
        window=self.wallet_windows[wallet_name]
        try:
            l = mode(window, self, wallet_name, password=password, manager=manager)
            tab = window.create_list_tab(l)
            i = window.tabs.indexOf(self.lw_tabs.get(wallet_name, None))

            self.lw_tabs[wallet_name] = tab
            self.lw_tab[wallet_name] = l
            window.tabs.addTab(tab, QIcon(":icons/preferences.png"), _('Last Will'))
            window.tabs.removeTab(i)
        except:
            return
