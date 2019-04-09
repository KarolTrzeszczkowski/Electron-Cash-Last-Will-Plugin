from electroncash.address import  OpCodes
import time


EXPIRY =time.strptime("1 7 2019", "%d %m %Y")

def make_opreturn(data):
    """Turn data bytes into a single-push opreturn script"""
    if len(data) < 76:
        return bytes((OpCodes.OP_RETURN, len(data))) + data
    elif len(data) < 256:
        return bytes((OpCodes.OP_RETURN, 76, len(data))) + data
    else:
        raise ValueError(data)


def is_expired():
    now=time.localtime(time.time())
    return EXPIRY<now