from .last_will_contract import LastWillContract
from electroncash.address import Address
from itertools import permutations


def find_contract(wallet):
    """Searching transactions for the one maching contract
    by creating contracts from outputs"""
    for hash, t in wallet.transactions.items():
        out = t.outputs()
        address=''
        if len(out) >4:
            address=get_contract_address(out)
            candidates=get_candidates(out)
            for c in candidates:
                will = LastWillContract(c)
                if will.address.to_ui_string()==address:
                    print("returning")
                    return t, will, find_my_role(c, wallet)


def get_contract_address(outputs):
    """Finds p2sh output"""
    for o in outputs:
        if not isinstance(o[1],Address):
            continue
        if o[1].kind==1:
            print("got address")
            return o[1].to_ui_string()

def get_candidates(outputs):
    """Creates all permutations of addresses that are not p2sh type"""
    candidates=[]
    for o1, o2, o3 in permutations(outputs, 3):
        if not (isinstance(o1[1],Address) and isinstance(o2[1],Address) and isinstance(o3[1],Address)):
            continue
        if o1[1].kind or o2[1].kind or o3[1].kind:
            continue
        candidates.append([o1[1],o2[1],o3[1]])
    print("got candidates")
    return candidates

def find_my_role(candidates, wallet):
    """Returns my role in this contract. 1 if this is refreshing wallet,
    2 if cold and 3 if it's inheritors wallet"""
    for counter, a in enumerate(candidates, start=0):
        if wallet.is_mine(a):
            return counter

