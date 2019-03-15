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
    """Contract of last will, that is timelocked for inheritor unless the creator refresh it
    from the hot wallet or spend from the cold wallet."""

    def __init__(self, addresses):
        self.time1=7
        self.time2=0
        self.addresses=addresses
        self.redeemscript2 = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(addresses[2].hash160), addresses[2].hash160,
            3, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
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
                        3, self.time1, self.time2, 64, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP,
                        5, Op.OP_PICK, Op.OP_HASH160, Op.OP_OVER, Op.OP_EQUALVERIFY, 4, Op.OP_PICK,
                        Op.OP_6, Op.OP_PICK, Op.OP_CHECKSIG,
                        Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                    Op.OP_ELSE,
                        Op.OP_FALSE,
                    Op.OP_ENDIF,
                Op.OP_ENDIF,
            Op.OP_ENDIF
        ])

        self.redeemscript = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(addresses[2].hash160), addresses[2].hash160,
            Op.OP_3, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
            Op.OP_IF,
                Op.OP_6, Op.OP_PICK, Op.OP_HASH160, Op.OP_3,
                Op.OP_PICK, Op.OP_EQUALVERIFY, Op.OP_5, Op.OP_PICK, Op.OP_7, Op.OP_PICK, Op.OP_CHECKSIGVERIFY, Op.OP_5,
                Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_8, Op.OP_PICK, Op.OP_CHECKDATASIGVERIFY, Op.OP_4, Op.OP_PICK,
                Op.OP_4, Op.OP_SPLIT, Op.OP_DROP, Op.OP_5, Op.OP_PICK, Op.OP_6, Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP,
                40, Op.OP_SUB, Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, 32, Op.OP_SPLIT, Op.OP_DROP, Op.OP_7,
                Op.OP_PICK, Op.OP_8, Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP, 44, Op.OP_SUB, Op.OP_SPLIT, Op.OP_DROP,
                Op.OP_DUP, 104, Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, Op.OP_OVER, Op.OP_SIZE, Op.OP_NIP, Op.OP_8,
                Op.OP_SUB, Op.OP_SPLIT, Op.OP_6, Op.OP_PICK, Op.OP_BIN2NUM, Op.OP_2, Op.OP_GREATERTHANOREQUAL, Op.OP_VERIFY,
                Op.OP_DUP, Op.OP_2, Op.OP_PICK, Op.OP_CAT, Op.OP_HASH256, Op.OP_5, Op.OP_PICK, Op.OP_EQUAL, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
                    Op.OP_3, Op.OP_PICK, Op.OP_2, Op.OP_EQUAL,
                Op.OP_IF,
                    Op.OP_5, Op.OP_PICK, Op.OP_HASH160, Op.OP_2, Op.OP_PICK, Op.OP_EQUALVERIFY, Op.OP_4, Op.OP_PICK, Op.OP_6,
                    Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_ELSE,
                        Op.OP_3, Op.OP_PICK, Op.OP_3, Op.OP_EQUAL,
                    Op.OP_IF,
                        7, 0, 64, Op.OP_CHECKSEQUENCEVERIFY,
                        Op.OP_DROP, Op.OP_5, Op.OP_PICK, Op.OP_HASH160, Op.OP_OVER, Op.OP_EQUALVERIFY, Op.OP_4, Op.OP_PICK, Op.OP_6,
                        Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                    Op.OP_ELSE,
                        Op.OP_FALSE,
                    Op.OP_ENDIF,
                Op.OP_ENDIF,
            Op.OP_ENDIF
        ])

        assert 76 < len(self.redeemscript) <= 255  # simplify push in scriptsig; note len is around 200.
        self.address = Address.from_multisig_script(self.redeemscript)


class LastWillContractManager:
    """A device that spends the Last Will in three different ways."""
    def __init__(self,tx, contract, pub, priv, mode):

        self.tx=tx[0]
        self.mode = mode
        self.public = pub
        self.keypair = {pub[0]: (priv, True)}
        self.contract = contract
        self.dummy_scriptsig = '01' * (140 + len(self.contract.redeemscript))  # make dummy scripts of correct size for size estimation.
        self.sequence=0
        self.value=int(self.tx.get('value'))
        if mode==2:
            self.sequence=self.contract.time1+2**22
        self.txin = dict(
            prevout_hash = self.tx.get('tx_hash'),
            prevout_n = int(self.tx.get('tx_pos')),
            sequence = self.sequence,
            scriptSig = self.dummy_scriptsig,
            type = 'unknown',
            address = self.contract.address,
            scriptCode = self.contract.redeemscript.hex(),
            num_sig = 1,
            signatures = [None],
            x_pubkeys = pub,
            value = self.value,
            )



    def signtx(self, tx):
        """generic tx signer for compressed pubkey"""
        tx.sign(self.keypair)

    def completetx(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`). `secret` may be bytes
        (if redeeming) or None (if refunding).

        This works on multiple utxos if needed.
        """
        pub = bytes.fromhex(self.public[0])
        for txin in tx.inputs():
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            if txin['scriptSig'] == self.dummy_scriptsig:
                script = [
                    len(pub), pub,
                    len(sig), sig,
                    76, len(self.contract.redeemscript), self.contract.redeemscript, # Script shorter than 75 bits
                    ]
            txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()

    def completetx_ref(self, tx):

        pub = bytes.fromhex(self.public[0])
        index=0
        for i, inp in enumerate(tx.inputs()):
            if inp.get('address').kind==1:
                index=i
        preimage=bytes.fromhex(tx.serialize_preimage(index))
        print("Preimage:")
        print(preimage)
        for txin in tx.inputs():
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            if txin['scriptSig'] == self.dummy_scriptsig:
                script = [
                    len(pub), pub,
                    len(sig), sig,
                    77, len(preimage).to_bytes(2, byteorder='little'), preimage,
                    76, len(self.contract.redeemscript), self.contract.redeemscript, # Script shorter than 75 bits
                    ]
            txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()

