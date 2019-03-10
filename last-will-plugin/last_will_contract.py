from ecdsa.ecdsa import curve_secp256k1, generator_secp256k1
from electroncash.bitcoin import ser_to_point, point_to_ser
from electroncash.address import Address, Script, hash160, ScriptOutput, OpCodes
from electroncash.address import OpCodes as Op
import hashlib
import time
LOCKTIME_THRESHOLD = 500000000

def joinbytes(iterable):
    """Joins an iterable of bytes and/or integers into a single byte string"""
    return b''.join((bytes((x,)) if isinstance(x,int) else x) for x in iterable)

class LastWillContract:
    """Contract of last will, that is timelocked for inheritor unless the creator bump it
    from the hot wallet or spend from the cold wallet."""
    def __init__(self,addresses, privs, wallet):

        self.publics = [wallet.get_public_keys(a) for a in addresses]
        #self.keypairs_ref = {self.publics[0][0]: (privs[0], True)}
        days=0.04
        self.seconds= int(time.time()) + int(days * 24 * 60 * 60)
        seconds_bytes=format_time(self.seconds)

        self.redeemscript = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(addresses[2].hash160), addresses[2].hash160,
            3,
            Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
            Op.OP_IF,
                5, Op.OP_PICK, Op.OP_HASH160, 3, Op.OP_PICK,
                Op.OP_EQUALVERIFY, 4, Op.OP_PICK, 6, Op.OP_PICK,
                Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
                3, Op.OP_PICK, 2, Op.OP_EQUAL,
                Op.OP_IF,
                    5, Op.OP_PICK, Op.OP_HASH160, 2, Op.OP_PICK,
                    Op.OP_EQUALVERIFY, 4, Op.OP_PICK, 6, Op.OP_PICK, Op.OP_CHECKSIG,
                    Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_ELSE,
                    3, Op.OP_PICK, 3, Op.OP_EQUAL,
                    Op.OP_IF,
                        len(seconds_bytes), seconds_bytes, Op.OP_CHECKLOCKTIMEVERIFY, Op.OP_DROP,
                        5, Op.OP_PICK, Op.OP_HASH160, Op.OP_OVER, Op.OP_EQUALVERIFY, 4, Op.OP_PICK,
                        Op.OP_6, Op.OP_PICK, Op.OP_CHECKSIG,
                        Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                    Op.OP_ELSE,
                        Op.OP_FALSE,
                    Op.OP_ENDIF,
                Op.OP_ENDIF,
            Op.OP_ENDIF
        ])



        print(len(self.redeemscript))
        assert 76< len(self.redeemscript) <= 255  # simplify push in scriptsig; note len is around 200.


        self.address = Address.from_multisig_script(self.redeemscript)
        self.dummy_scriptsig_redeem = '01'*(140 + len(self.redeemscript)) # make dummy scripts of correct size for size estimation.


    def makeinput(self, prevout_hash, prevout_n, value):
        """
        Construct an unsigned input for adding to a transaction. scriptSig is
        set to a dummy value, for size estimation.

        (note: Transaction object will fail to broadcast until you sign and run `completetx`)
        """

        scriptSig = self.dummy_scriptsig_redeem
        pubkey = self.publics[0]

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
            x_pubkeys = pubkey,
            value = value,
            )
        return txin

    def signtx(self, tx):
        """generic tx signer for compressed pubkey"""
        #tx.sign(self.keypairs)

    def completetx(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`). `secret` may be bytes
        (if redeeming) or None (if refunding).

        This works on multiple utxos if needed.
        """
        pub = bytes.fromhex(self.publics[0][0])
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
                    len(pub), pub,
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