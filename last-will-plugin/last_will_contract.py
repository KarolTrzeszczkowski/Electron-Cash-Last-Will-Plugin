from ecdsa.ecdsa import curve_secp256k1, generator_secp256k1
from electroncash.bitcoin import ser_to_point, point_to_ser
from electroncash.address import Address, Script, hash160, ScriptOutput
import hashlib
from .op_codes import OpCodes
import time
LOCKTIME_THRESHOLD = 500000000

def joinbytes(iterable):
    """Joins an iterable of bytes and/or integers into a single byte string"""
    return b''.join((bytes((x,)) if isinstance(x,int) else x) for x in iterable)

class LastWillContract:
    """Contract for making coins that can only be spent on BCH chains supporting
    OP_CHECKDATASIGVERIFY, with backup clause for recovering dust on non-supporting
    chains."""
    def __init__(self, master_privkey):
        G = generator_secp256k1
        order = G.order()
        # hard derivation (irreversible):
        x = int.from_bytes(hashlib.sha512(b'Split1' + master_privkey.to_bytes(32, 'big')).digest(), 'big')
        self.priv1 = 1 + (x % (order-1))
        self.pub1ser = point_to_ser(self.priv1 * G, True)
        self.keypairs = {self.pub1ser.hex() : (self.priv1.to_bytes(32, 'big'), True)}



        days=0.04
        self.seconds= int(time.time()) + int(days * 24 * 60 * 60)
        seconds_bytes=format_time(self.seconds)

        self.redeemscript = joinbytes([
            len(seconds_bytes), seconds_bytes, OpCodes.OP_CHECKLOCKTIMEVERIFY,
            OpCodes.OP_DROP,
            len(self.pub1ser), self.pub1ser,
            OpCodes.OP_CHECKSIG ])

        print(len(self.redeemscript))
        # assert 76< len(self.redeemscript) <= 255  # simplify push in scriptsig; note len is around 200.
        self.address = Address.from_multisig_script(self.redeemscript)
        self.dummy_scriptsig_redeem = '01'*(74 + len(self.redeemscript)) # make dummy scripts of correct size for size estimation.


    def makeinput(self, prevout_hash, prevout_n, value):
        """
        Construct an unsigned input for adding to a transaction. scriptSig is
        set to a dummy value, for size estimation.

        (note: Transaction object will fail to broadcast until you sign and run `completetx`)
        """

        scriptSig = self.dummy_scriptsig_redeem
        pubkey = self.pub1ser

        txin = dict(
            prevout_hash = prevout_hash,
            prevout_n = prevout_n,
            sequence = 0,
            scriptSig = scriptSig,

            type = 'unknown',
            address = self.address,
            scriptCode = self.redeemscript.hex(),
            num_sig = 1,
            signatures = [None],
            x_pubkeys = [pubkey.hex()],
            value = value,
            )
        return txin

    def signtx(self, tx):
        """generic tx signer for compressed pubkey"""
        tx.sign(self.keypairs)

    def completetx(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`). `secret` may be bytes
        (if redeeming) or None (if refunding).

        This works on multiple utxos if needed.
        """

        for txin in tx.inputs():
            # find matching inputs
            if txin['address'] != self.address:
                continue
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            if txin['scriptSig'] == self.dummy_scriptsig_redeem:
                script = [
                    len(sig), sig,
                    len(self.redeemscript), self.redeemscript, # Script shorter than 75 bits
                    ]
            txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()



def format_time(seconds):

    print("Transaction Locktime in seconds: "+ str(seconds))
    print("Current time: "+ str(time.time()))

    assert seconds >= LOCKTIME_THRESHOLD
    assert seconds < 0x8000000000

    if seconds < 0x80000000:
        # until year 2038 use 4 byte form
        time_bytes = seconds.to_bytes(4, 'little')
    else:
        # from 2038 onwards our number cannot fit into 4 bytes since the high
        # bit is used for sign, in bitcoin script.
        time_bytes = seconds.to_bytes(5, 'little')

    assert time_bytes[-1] != 0 and not time_bytes[-1] & 0x80
    return time_bytes
# The transaction was rejected because it contians a non-mandatory script verify flag.