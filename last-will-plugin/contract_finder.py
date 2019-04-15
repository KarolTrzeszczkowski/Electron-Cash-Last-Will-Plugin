from .last_will_contract import LastWillContract
from electroncash.address import Address, ScriptOutput
from itertools import permutations
from electroncash.transaction import Transaction


def find_contract(wallet,a = 'network'):
    """Searching transactions for the one maching contract
    by creating contracts from outputs"""
    contracts=[]
    for hash, t in wallet.transactions.items():
        out = t.outputs()
        address = ''
        if len(out) > 3:
            address = get_contract_address(out)
            candidates = get_candidates(out)
            for c in candidates:
                will = LastWillContract(c)
                if will.address.to_ui_string()==address:
                    refreshing=c[0]
                    response = wallet.network.synchronous_get(
                        ("blockchain.scripthash.listunspent", [will.address.to_scripthash_hex()]))
                    if unfunded_contract(response) : #skip unfunded and ended contracts
                        continue
                    utxo=response[0][0]
                    if len(response)>1:
                        utxo= filter_trick_utxos(response[0],wallet,refreshing,will.address)
                    if a == 'network':
                        contracts.append(( utxo, will, find_my_role(c, wallet)))
                    else:
                        contracts.append(t.as_dict())
    return contracts

def extract_contract_data(tx):
    transaction=Transaction(tx)
    address = get_contract_address(transaction.outputs())
    candidates = get_candidates(transaction.outputs())
    for c in candidates:
        will = LastWillContract(c)
        if will.address.to_ui_string()==address:
            return will

def unfunded_contract(r):
    """Checks if the contract is funded"""
    s = False
    if len(r) == 0:
        s = True
    for t in r:
        if t.get('value') == 0: # when contract was drained by fees it's still in utxo
            s = True
    return s

def filter_trick_utxos(r, wallet, ref, contract):
    """Mallicious actor may try to trick a plugin by sending dust to the contract address"""
    for utxo in r:
        request = ('blockchain.transaction.get',[utxo.get('tx_hash')])
        tx = Transaction(wallet.network.synchronous_get(request))
        if tx.inputs().get('address') != ref or tx.inputs().get('address') != contract:
            continue
        return utxo


def get_contract_address(outputs):
    """Finds p2sh output"""
    for o in outputs:
        if isinstance(o[1], ScriptOutput):
            try:
                return o[1].to_ui_string().split("'")[1]
            except:
                pass

def get_candidates(outputs):
    """Creates all permutations of addresses that are not p2sh type"""
    candidates = []
    for o1, o2, o3 in permutations(outputs, 3):
        if not (isinstance(o1[1], Address) and isinstance(o2[1], Address) and isinstance(o3[1], Address)):
            continue
        if o1[1].kind or o2[1].kind or o3[1].kind:
            continue
        candidates.append([o1[1], o2[1], o3[1]])
    return candidates

def find_my_role(candidates, wallet):
    """Returns my role in this contract. 1 if this is refreshing wallet,
    2 if cold and 3 if it's inheritors wallet"""
    for counter, a in enumerate(candidates, start=0):
        if wallet.is_mine(a):
            return counter, a

