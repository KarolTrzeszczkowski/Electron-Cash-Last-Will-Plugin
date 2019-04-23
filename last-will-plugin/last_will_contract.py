from electroncash.bitcoin import regenerate_key, MySigningKey, Hash
from electroncash.address import Address, OpCodes as Op
import ecdsa
from electroncash.plugins import hook
from math import ceil

import time
LOCKTIME_THRESHOLD = 500000000

def joinbytes(iterable):
    """Joins an iterable of bytes and/or integers into a single byte string"""
    return b''.join((bytes((x,)) if isinstance(x,int) else x) for x in iterable)


class LastWillContract:
    """Contract of last will, that is timelocked for inheritor unless the creator refresh it
    from the hot wallet or spend from the cold wallet."""

    def __init__(self, addresses):

        self.time1 = (180*3600*24)//512
        self.time_bytes = (self.time1).to_bytes(2,'little')
        self.time2= (7*3600*24)//512
        self.time2_bytes = (self.time2).to_bytes(2,'little')
        self.addresses=addresses

        assert len(self.time2_bytes)==2
        assert len(self.time_bytes)==2


        self.redeemscript = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(addresses[2].hash160), addresses[2].hash160,
            Op.OP_3, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
            Op.OP_IF,
                Op.OP_12, Op.OP_PICK, Op.OP_HASH160, Op.OP_3, Op.OP_PICK, Op.OP_EQUALVERIFY, Op.OP_11, Op.OP_PICK, Op.OP_13,
                Op.OP_PICK, Op.OP_CHECKSIGVERIFY, Op.OP_10, Op.OP_PICK, Op.OP_10, Op.OP_PICK, Op.OP_CAT, Op.OP_9,
                Op.OP_PICK, Op.OP_CAT, Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_7, Op.OP_PICK, Op.OP_CAT, Op.OP_6, Op.OP_PICK,
                Op.OP_CAT, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_12, Op.OP_PICK, Op.OP_SIZE, Op.OP_1SUB, Op.OP_SPLIT,
                Op.OP_DROP, Op.OP_OVER, Op.OP_SHA256, Op.OP_15, Op.OP_PICK, Op.OP_CHECKDATASIGVERIFY, 2, 232, 3, Op.OP_9,
                Op.OP_PICK, Op.OP_BIN2NUM, Op.OP_OVER, Op.OP_SUB, Op.OP_8, Op.OP_NUM2BIN, 1, 135, 1, 169, 1, 20, 1, 23,
                Op.OP_15, Op.OP_PICK, Op.OP_TRUE, Op.OP_SPLIT, Op.OP_NIP, 3, self.time2_bytes, 64, Op.OP_CHECKSEQUENCEVERIFY,
                Op.OP_DROP, 1, 18, Op.OP_PICK, Op.OP_BIN2NUM, Op.OP_2, Op.OP_GREATERTHANOREQUAL, Op.OP_VERIFY, Op.OP_5,
                Op.OP_PICK, Op.OP_2, Op.OP_PICK, Op.OP_CAT, Op.OP_4, Op.OP_PICK, Op.OP_CAT, Op.OP_3, Op.OP_PICK, Op.OP_CAT,
                Op.OP_OVER, Op.OP_HASH160, Op.OP_CAT, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_HASH256, Op.OP_14, Op.OP_PICK,
                Op.OP_EQUAL, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
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
                        3, self.time_bytes, 64, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP, Op.OP_5, Op.OP_PICK, Op.OP_HASH160, Op.OP_OVER,
                        Op.OP_EQUALVERIFY, Op.OP_4, Op.OP_PICK, Op.OP_6, Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP,
                        Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
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
        self.tx=tx
        self.mode = mode
        self.public = pub
        self.keypair = {pub[0]: (priv, True)}
        self.contract = contract
        self.dummy_scriptsig = '00'*(74 + len(self.contract.redeemscript))

        if mode == 0:
            self.sequence=2**22+self.contract.time2
        elif mode == 2:
            self.sequence=2**22+self.contract.time1
        else:
            self.sequence = 0
        self.value=int(self.tx.get('value'))

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


    @hook
    def sign_tx(self, tx):
        """generic tx signer for compressed pubkey"""
        tx.sign(self.keypair)
        self.completetx(tx)

    def signtx(self, tx):
        """generic tx signer for compressed pubkey"""
        tx.sign(self.keypair)


    def completetx(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`).
        This works on multiple utxos if needed.
        """
        if self.mode == 1:
            option = Op.OP_2
        else :
            option = Op.OP_3
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
                    option, 76, len(self.contract.redeemscript), self.contract.redeemscript,
                    ]
                print("scriptSig length " + str(joinbytes(script).hex().__sizeof__()))
            txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()

    def completetx_ref(self, tx):

        pub = bytes.fromhex(self.public[0])

        for i, txin in enumerate(tx.inputs()):
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            preimage=bytes.fromhex(tx.serialize_preimage(i))
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            print("Signature size:" + str(len(sig)))
            if txin['scriptSig'] == self.dummy_scriptsig:
                self.checkd_data_sig(sig,preimage,self.public[0])

                ver=preimage[:4]
                hPhSo=preimage[4:104]
                scriptCode=preimage[104:-52]
                assert len(scriptCode)<256 and len(scriptCode)>75
                value=preimage[-52:-44]
                nSequence=preimage[-44:-40]
                hashOutput=preimage[-40:-8]
                tail=preimage[-8:]

                script = [
                    len(pub), pub,
                    len(sig), sig,
                    len(ver), ver,
                    76, len(hPhSo), hPhSo,
                    76, len(scriptCode), scriptCode,
                    len(value), value,
                    len(nSequence), nSequence,
                    len(hashOutput), hashOutput,
                    len(tail), tail,
                    Op.OP_1, 76, len(self.contract.redeemscript), self.contract.redeemscript,
                    ]
                print("scriptSig length "+ str(joinbytes(script).hex().__sizeof__()))
            txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()

    def checkd_data_sig(self,sig,pre,pk):
        sec, compressed = self.keypair.get(pk)
        pre_hash = Hash(pre)
        pkey = regenerate_key(sec)
        secexp = pkey.secret
        private_key = MySigningKey.from_secret_exponent(secexp, curve=ecdsa.SECP256k1)
        public_key = private_key.get_verifying_key()
        print("Data signature ok:")
        print(public_key.verify_digest(sig[:-1], pre_hash, sigdecode=ecdsa.util.sigdecode_der))

