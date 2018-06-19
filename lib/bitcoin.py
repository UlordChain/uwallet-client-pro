# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os
import sys
sys.path.append(os.path.realpath('.'))#qpc
from cryptohello_hash import cryptohello_hash

import hashlib
import base64
import os
import re
import hmac

import version
from util import print_error, InvalidPassword

import ecdsa
import aes

################################## transactions

FEE_STEP = 10000
RECOMMENDED_FEE = 20000
COINBASE_MATURITY = 100
COIN = 100000000

# supported types of transction outputs
TYPE_ADDRESS = 0
TYPE_PUBKEY  = 1
TYPE_SCRIPT  = 2


# AES encryption
EncodeAES = lambda secret, s: base64.b64encode(aes.encryptData(secret,s))
DecodeAES = lambda secret, e: aes.decryptData(secret, base64.b64decode(e))

def strip_PKCS7_padding(s):
    """return s stripped of PKCS7 padding"""
    if len(s)%16 or not s:
        raise ValueError("String of len %d can't be PCKS7-padded" % len(s))
    numpads = ord(s[-1])
    if numpads > 16:
        raise ValueError("String ending with %r can't be PCKS7-padded" % s[-1])
    if s[-numpads:] != numpads*chr(numpads):
        raise ValueError("Invalid PKCS7 padding")
    return s[:-numpads]

# backport padding fix to AES module
aes.strip_PKCS7_padding = strip_PKCS7_padding

def aes_encrypt_with_iv(key, iv, data):
    mode = aes.AESModeOfOperation.modeOfOperation["CBC"]
    key = map(ord, key)
    iv = map(ord, iv)
    data = aes.append_PKCS7_padding(data)
    keysize = len(key)
    assert keysize in aes.AES.keySize.values(), 'invalid key size: %s' % keysize
    moo = aes.AESModeOfOperation()
    (mode, length, ciph) = moo.encrypt(data, mode, key, keysize, iv)
    return ''.join(map(chr, ciph))

def aes_decrypt_with_iv(key, iv, data):
    mode = aes.AESModeOfOperation.modeOfOperation["CBC"]
    key = map(ord, key)
    iv = map(ord, iv)
    keysize = len(key)
    assert keysize in aes.AES.keySize.values(), 'invalid key size: %s' % keysize
    data = map(ord, data)
    moo = aes.AESModeOfOperation()
    decr = moo.decrypt(data, None, mode, key, keysize, iv)
    decr = strip_PKCS7_padding(decr)
    return decr



def pw_encode(s, password):
    if password:
        secret = Hash(password)
        return EncodeAES(secret, s.encode("utf8"))
    else:
        return s


def pw_decode(s, password):
    if password is not None:
        secret = Hash(password)
        try:
            d = DecodeAES(secret, s).decode("utf8")
        except Exception:
            raise InvalidPassword()
        return d
    else:
        return s


def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')


def hex_to_int(s):
    return int('0x' + s[::-1].encode('hex'), 16)

def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)


def var_int(i):
    # https://en.bitcoin.it/wiki/Protocol_specification#Variable_length_integer
    if i<0xfd:
        return int_to_hex(i)
    elif i<=0xffff:
        return "fd"+int_to_hex(i,2)
    elif i<=0xffffffff:
        return "fe"+int_to_hex(i,4)
    else:
        return "ff"+int_to_hex(i,8)


def op_push(i):
    if i<0x4c:
        return int_to_hex(i)
    elif i<0xff:
        return '4c' + int_to_hex(i)
    elif i<0xffff:
        return '4d' + int_to_hex(i,2)
    else:
        return '4e' + int_to_hex(i,4)


def sha256(x):
    return hashlib.sha256(x).digest()


def Hash(x):
    if type(x) is unicode: x=x.encode('utf-8')
    return sha256(sha256(x))

def Hash_Header(x):
    if type(x) is unicode:
        x = x.encode('utf-8')
    return cryptohello_hash(x,1) #qpc


hash_encode = lambda x: x[::-1].encode('hex')
hash_decode = lambda x: x.decode('hex')[::-1]
hmac_sha_512 = lambda x,y: hmac.new(x, y, hashlib.sha512).digest()

def is_new_seed(x, prefix=version.SEED_PREFIX):
    import mnemonic
    x = mnemonic.normalize_text(x)
    s = hmac_sha_512("Seed version", x.encode('utf8')).encode('hex')
    return s.startswith(prefix)


def is_old_seed(seed):
    import old_mnemonic,mnemonic
    seed = mnemonic.normalize_text(seed)

    words = seed.strip().split()
    try:
        old_mnemonic.mn_decode(words)
        uses_uwallet_words = True
    except Exception:
        uses_uwallet_words = False
    try:
        seed.decode('hex')
        is_hex = (len(seed) == 32 or len(seed) == 64)
    except Exception:
        is_hex = False
    return is_hex or (uses_uwallet_words and (len(words) == 12 or len(words) == 24))
    # from . import old_mnemonic, mnemonic
    # seed = mnemonic.normalize_text(seed)
    # words = seed.split()
    # try:
    #     # checks here are deliberately left weak for legacy reasons, see #3149
    #     old_mnemonic.mn_decode(words)
    #     uses_electrum_words = True
    # except Exception:
    #     uses_electrum_words = False
    # try:
    #     seed = bfh(seed)
    #     is_hex = (len(seed) == 16 or len(seed) == 32)
    # except Exception:
    #     is_hex = False
    # return is_hex or (uses_electrum_words and (len(words) == 12 or len(words) == 24))

bfh = bytearray.fromhex

def seed_type(x):
    if is_old_seed(x):
        return 'old'
    elif is_new_seed(x):
        return 'standard'
    elif is_new_seed(x, version.SEED_PREFIX_2FA):
        return '2fa'
    return ''

is_seed = lambda x: bool(seed_type(x))

# def isSeed(s):
#     b = Mnemonic_bip39('english').check(s)
#     return b
# pywallet openssl private key implementation

def i2o_ECPublicKey(pubkey, compressed=False):
    # public keys are 65 bytes long (520 bits)
    # 0x04 + 32-byte X-coordinate + 32-byte Y-coordinate
    # 0x00 = point at infinity, 0x02 and 0x03 = compressed, 0x04 = uncompressed
    # compressed keys: <sign> <x> where <sign> is 0x02 if y is even and 0x03 if y is odd
    if compressed:
        if pubkey.point.y() & 1:
            key = '03' + '%064x' % pubkey.point.x()
        else:
            key = '02' + '%064x' % pubkey.point.x()
    else:
        key = '04' + \
              '%064x' % pubkey.point.x() + \
              '%064x' % pubkey.point.y()

    return key.decode('hex')

# end pywallet openssl private key implementation



############ functions from pywallet #####################

def hash_160(public_key):
    if 'ANDROID_DATA' in os.environ:
        from Crypto.Hash import RIPEMD
        md = RIPEMD.new()
    else:
        md = hashlib.new('ripemd')
    md.update(sha256(public_key))
    return md.digest()

def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)

def hash_160_to_bc_address(h160, addrtype = 68): #68#130
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return base_encode(addr, base=58)

def bc_address_to_hash_160(addr):
    bytes = base_decode(addr, 25, base=58)
    return ord(bytes[0]), bytes[1:21]


__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
assert len(__b58chars) == 58

__b43chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$*+-./:'
assert len(__b43chars) == 43


def base_encode(v, base):
    """ encode v, which is a string of bytes, to base58."""
    if base == 58:
        chars = __b58chars
    elif base == 43:
        chars = __b43chars
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)
    result = ''
    while long_value >= base:
        div, mod = divmod(long_value, base)
        result = chars[mod] + result
        long_value = div
    result = chars[long_value] + result
    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break
    return (chars[0]*nPad) + result


def base_decode(v, length, base):
    """ decode v into a string of len bytes."""
    if base == 58:
        chars = __b58chars
    elif base == 43:
        chars = __b43chars
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += chars.find(c) * (base**i)
    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result
    nPad = 0
    for c in v:
        if c == chars[0]: nPad += 1
        else: break
    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None
    return result


def EncodeBase58Check(vchIn):
    hash = Hash(vchIn)
    return base_encode(vchIn + hash[0:4], base=58)


def DecodeBase58Check(psz):
    vchRet = base_decode(psz, None, base=58)
    key = vchRet[0:-4]
    csum = vchRet[-4:]
    hash = Hash(key)
    cs32 = hash[0:4]
    if cs32 != csum:
        return None
    else:
        return key


def PrivKeyToSecret(privkey):
    return privkey[9:9+32]


def SecretToASecret(secret, compressed=False, addrtype=0):
    vchIn = chr((addrtype+128)&255) + secret
    if compressed: vchIn += '\01'
    return EncodeBase58Check(vchIn)

def ASecretToSecret(key, addrtype=0):
    vch = DecodeBase58Check(key)
    if vch and vch[0] == chr((addrtype+128)&255):
        return vch[1:]
    elif is_minikey(key):
        return minikey_to_private_key(key)
    else:
        return False

def regenerate_key(sec):
    b = ASecretToSecret(sec)
    if not b:
        return False
    b = b[0:32]
    return EC_KEY(b)


def GetPubKey(pubkey, compressed=False):
    return i2o_ECPublicKey(pubkey, compressed)


def GetSecret(pkey):
    return ('%064x' % pkey.secret).decode('hex')


def is_compressed(sec):
    b = ASecretToSecret(sec)
    return len(b) == 33


def public_key_from_private_key(sec):
    # rebuild public key from private key, compressed or uncompressed
    pkey = regenerate_key(sec)
    assert pkey
    compressed = is_compressed(sec)
    public_key = GetPubKey(pkey.pubkey, compressed)
    return public_key.encode('hex')


def address_from_private_key(sec):
    public_key = public_key_from_private_key(sec)
    address = public_key_to_bc_address(public_key.decode('hex'))
    return address


def is_valid(addr):
    return is_address(addr)


def is_address(addr):
    ADDRESS_RE = re.compile('[1-9A-HJ-NP-Za-km-z]{26,}\\Z')
    if not ADDRESS_RE.match(addr):
        return False
    try:
        addrtype, h = bc_address_to_hash_160(addr)
    except Exception:
        return False
    if addrtype not in [0, 68]:#68#130
        return False
    return addr == hash_160_to_bc_address(h, addrtype)


def is_private_key(key):
    try:
        k = ASecretToSecret(key)
        return k is not False
    except:
        return False


########### end pywallet functions #######################

def is_minikey(text):
    # Minikeys are typically 22 or 30 characters, but this routine
    # permits any length of 20 or more provided the minikey is valid.
    # A valid minikey must begin with an 'S', be in base58, and when
    # suffixed with '?' have its SHA256 hash begin with a zero byte.
    # They are widely used in Casascius physical bitoins.
    return (len(text) >= 20 and text[0] == 'S'
            and all(c in __b58chars for c in text)
            and ord(sha256(text + '?')[0]) == 0)

def minikey_to_private_key(text):
    return sha256(text)

from ecdsa.ecdsa import curve_secp256k1, generator_secp256k1
from ecdsa.curves import SECP256k1
from ecdsa.ellipticcurve import Point
from ecdsa.util import string_to_number, number_to_string

def msg_magic(message):
    varint = var_int(len(message))
    encoded_varint = "".join([chr(int(varint[i:i+2], 16)) for i in xrange(0, len(varint), 2)])
    return "\x18Bitcoin Signed Message:\n" + encoded_varint + message


def verify_message(address, sig, message):
    try:
        public_key, compressed = pubkey_from_signature(sig, message)
        # check public key using the address
        pubkey = point_to_ser(public_key.pubkey.point, compressed)
        addr = public_key_to_bc_address(pubkey)
        if address != addr:
            raise Exception("Bad signature")
        # check message
        h = Hash(msg_magic(message))
        public_key.verify_digest(sig[1:], h, sigdecode = ecdsa.util.sigdecode_string)
        return True
    except Exception as e:
        print_error("Verification error: {0}".format(e))
        return False


def encrypt_message(message, pubkey):
    return EC_KEY.encrypt_message(message, pubkey.decode('hex'))


def chunks(l, n):
    return [l[i:i+n] for i in xrange(0, len(l), n)]


def ECC_YfromX(x,curved=curve_secp256k1, odd=True):
    _p = curved.p()
    _a = curved.a()
    _b = curved.b()
    for offset in range(128):
        Mx = x + offset
        My2 = pow(Mx, 3, _p) + _a * pow(Mx, 2, _p) + _b % _p
        My = pow(My2, (_p+1)/4, _p )

        if curved.contains_point(Mx,My):
            if odd == bool(My&1):
                return [My,offset]
            return [_p-My,offset]
    raise Exception('ECC_YfromX: No Y found')


def negative_point(P):
    return Point( P.curve(), P.x(), -P.y(), P.order() )


def point_to_ser(P, comp=True ):
    if comp:
        return ( ('%02x'%(2+(P.y()&1)))+('%064x'%P.x()) ).decode('hex')
    return ( '04'+('%064x'%P.x())+('%064x'%P.y()) ).decode('hex')


def ser_to_point(Aser):
    curve = curve_secp256k1
    generator = generator_secp256k1
    _r  = generator.order()
    assert Aser[0] in ['\x02','\x03','\x04']
    if Aser[0] == '\x04':
        return Point( curve, string_to_number(Aser[1:33]), string_to_number(Aser[33:]), _r )
    Mx = string_to_number(Aser[1:])
    return Point( curve, Mx, ECC_YfromX(Mx, curve, Aser[0]=='\x03')[0], _r )



class MyVerifyingKey(ecdsa.VerifyingKey):
    @classmethod
    def from_signature(klass, sig, recid, h, curve):
        """ See http://www.secg.org/download/aid-780/sec1-v2.pdf, chapter 4.1.6 """
        from ecdsa import util, numbertheory
        import msqr
        curveFp = curve.curve
        G = curve.generator
        order = G.order()
        # extract r,s from signature
        r, s = util.sigdecode_string(sig, order)
        # 1.1
        x = r + (recid/2) * order
        # 1.3
        alpha = ( x * x * x  + curveFp.a() * x + curveFp.b() ) % curveFp.p()
        beta = msqr.modular_sqrt(alpha, curveFp.p())
        y = beta if (beta - recid) % 2 == 0 else curveFp.p() - beta
        # 1.4 the constructor checks that nR is at infinity
        R = Point(curveFp, x, y, order)
        # 1.5 compute e from message:
        e = string_to_number(h)
        minus_e = -e % order
        # 1.6 compute Q = r^-1 (sR - eG)
        inv_r = numbertheory.inverse_mod(r,order)
        Q = inv_r * ( s * R + minus_e * G )
        return klass.from_public_point( Q, curve )


def pubkey_from_signature(sig, message):
    if len(sig) != 65:
        raise Exception("Wrong encoding")
    nV = ord(sig[0])
    if nV < 27 or nV >= 35:
        raise Exception("Bad encoding")
    if nV >= 31:
        compressed = True
        nV -= 4
    else:
        compressed = False
    recid = nV - 27
    h = Hash(msg_magic(message))
    return MyVerifyingKey.from_signature(sig[1:], recid, h, curve = SECP256k1), compressed


class MySigningKey(ecdsa.SigningKey):
    """Enforce low S values in signatures"""

    def sign_number(self, number, entropy=None, k=None):
        curve = SECP256k1
        G = curve.generator
        order = G.order()
        r, s = ecdsa.SigningKey.sign_number(self, number, entropy, k)
        if s > order/2:
            s = order - s
        return r, s


class EC_KEY(object):

    def __init__( self, k ):
        secret = string_to_number(k)
        self.pubkey = ecdsa.ecdsa.Public_key( generator_secp256k1, generator_secp256k1 * secret )
        self.privkey = ecdsa.ecdsa.Private_key( self.pubkey, secret )
        self.secret = secret

    def get_public_key(self, compressed=True):
        return point_to_ser(self.pubkey.point, compressed).encode('hex')

    def sign(self, msg_hash):
        private_key = MySigningKey.from_secret_exponent(self.secret, curve = SECP256k1)
        public_key = private_key.get_verifying_key()
        signature = private_key.sign_digest_deterministic(msg_hash, hashfunc=hashlib.sha256, sigencode = ecdsa.util.sigencode_string)
        assert public_key.verify_digest(signature, msg_hash, sigdecode = ecdsa.util.sigdecode_string)
        return signature

    def sign_message(self, message, is_compressed):
        signature = self.sign(Hash(msg_magic(message)))
        for i in range(4):
            sig = chr(27 + i + (4 if is_compressed else 0)) + signature
            try:
                self.verify_message(sig, message)
                return sig
            except Exception:
                continue
        else:
            raise Exception("error: cannot sign message")


    def verify_message(self, sig, message):
        public_key, compressed = pubkey_from_signature(sig, message)
        # check public key
        if point_to_ser(public_key.pubkey.point, compressed) != point_to_ser(self.pubkey.point, compressed):
            raise Exception("Bad signature")
        # check message
        h = Hash(msg_magic(message))
        public_key.verify_digest(sig[1:], h, sigdecode = ecdsa.util.sigdecode_string)


    # ECIES encryption/decryption methods; AES-128-CBC with PKCS7 is used as the cipher; hmac-sha256 is used as the mac

    @classmethod
    def encrypt_message(self, message, pubkey):

        pk = ser_to_point(pubkey)
        if not ecdsa.ecdsa.point_is_valid(generator_secp256k1, pk.x(), pk.y()):
            raise Exception('invalid pubkey')

        ephemeral_exponent = number_to_string(ecdsa.util.randrange(pow(2,256)), generator_secp256k1.order())
        ephemeral = EC_KEY(ephemeral_exponent)
        ecdh_key = point_to_ser(pk * ephemeral.privkey.secret_multiplier)
        key = hashlib.sha512(ecdh_key).digest()
        iv, key_e, key_m = key[0:16], key[16:32], key[32:]
        ciphertext = aes_encrypt_with_iv(key_e, iv, message)
        ephemeral_pubkey = ephemeral.get_public_key(compressed=True).decode('hex')
        encrypted = 'BIE1' + ephemeral_pubkey + ciphertext
        mac = hmac.new(key_m, encrypted, hashlib.sha256).digest()

        return base64.b64encode(encrypted + mac)


    def decrypt_message(self, encrypted):

        encrypted = base64.b64decode(encrypted)

        if len(encrypted) < 85:
            raise Exception('invalid ciphertext: length')

        magic = encrypted[:4]
        ephemeral_pubkey = encrypted[4:37]
        ciphertext = encrypted[37:-32]
        mac = encrypted[-32:]

        if magic != 'BIE1':
            raise Exception('invalid ciphertext: invalid magic bytes')

        try:
            ephemeral_pubkey = ser_to_point(ephemeral_pubkey)
        except AssertionError, e:
            raise Exception('invalid ciphertext: invalid ephemeral pubkey')

        if not ecdsa.ecdsa.point_is_valid(generator_secp256k1, ephemeral_pubkey.x(), ephemeral_pubkey.y()):
            raise Exception('invalid ciphertext: invalid ephemeral pubkey')

        ecdh_key = point_to_ser(ephemeral_pubkey * self.privkey.secret_multiplier)
        key = hashlib.sha512(ecdh_key).digest()
        iv, key_e, key_m = key[0:16], key[16:32], key[32:]
        if mac != hmac.new(key_m, encrypted[:-32], hashlib.sha256).digest():
            raise Exception('invalid ciphertext: invalid mac')

        return aes_decrypt_with_iv(key_e, iv, ciphertext)


###################################### BIP32 ##############################

random_seed = lambda n: "%032x"%ecdsa.util.randrange( pow(2,n) )
BIP32_PRIME = 0x80000000


def get_pubkeys_from_secret(secret):
    # public key
    private_key = ecdsa.SigningKey.from_string( secret, curve = SECP256k1 )
    public_key = private_key.get_verifying_key()
    K = public_key.to_string()
    K_compressed = GetPubKey(public_key.pubkey,True)
    return K, K_compressed


# Child private key derivation function (from master private key)
# k = master private key (32 bytes)
# c = master chain code (extra entropy for key derivation) (32 bytes)
# n = the index of the key we want to derive. (only 32 bits will be used)
# If n is negative (i.e. the 32nd bit is set), the resulting private key's
#  corresponding public key can NOT be determined without the master private key.
# However, if n is positive, the resulting private key's corresponding
#  public key can be determined without the master private key.
def CKD_priv(k, c, n):
    is_prime = n & BIP32_PRIME
    return _CKD_priv(k, c, rev_hex(int_to_hex(n,4)).decode('hex'), is_prime)

def _CKD_priv(k, c, s, is_prime):
    order = generator_secp256k1.order()
    keypair = EC_KEY(k)
    cK = GetPubKey(keypair.pubkey,True)
    data = chr(0) + k + s if is_prime else cK + s
    I = hmac.new(c, data, hashlib.sha512).digest()
    k_n = number_to_string( (string_to_number(I[0:32]) + string_to_number(k)) % order , order )
    c_n = I[32:]
    return k_n, c_n

# Child public key derivation function (from public key only)
# K = master public key
# c = master chain code
# n = index of key we want to derive
# This function allows us to find the nth public key, as long as n is
#  non-negative. If n is negative, we need the master private key to find it.
def CKD_pub(cK, c, n):
    if n & BIP32_PRIME: raise Exception
    return _CKD_pub(cK, c, rev_hex(int_to_hex(n,4)).decode('hex'))

# helper function, callable with arbitrary string
def _CKD_pub(cK, c, s):
    order = generator_secp256k1.order()
    I = hmac.new(c, cK + s, hashlib.sha512).digest()
    curve = SECP256k1
    pubkey_point = string_to_number(I[0:32])*curve.generator + ser_to_point(cK)
    public_key = ecdsa.VerifyingKey.from_public_point( pubkey_point, curve = SECP256k1 )
    c_n = I[32:]
    cK_n = GetPubKey(public_key.pubkey,True)
    return cK_n, c_n


BITCOIN_HEADER_PRIV = "0488ade4"
BITCOIN_HEADER_PUB = "0488b21e"

TESTNET_HEADER_PRIV = "04358394"
TESTNET_HEADER_PUB = "043587cf"

BITCOIN_HEADERS = (BITCOIN_HEADER_PUB, BITCOIN_HEADER_PRIV)
TESTNET_HEADERS = (TESTNET_HEADER_PUB, TESTNET_HEADER_PRIV)

def _get_headers(testnet):
    """Returns the correct headers for either testnet or bitcoin, in the form
    of a 2-tuple, like (public, private)."""
    if testnet:
        return TESTNET_HEADERS
    else:
        return BITCOIN_HEADERS


def deserialize_xkey(xkey):

    xkey = DecodeBase58Check(xkey)
    assert len(xkey) == 78

    xkey_header = xkey[0:4].encode('hex')
    # Determine if the key is a bitcoin key or a testnet key.
    if xkey_header in TESTNET_HEADERS:
        head = TESTNET_HEADER_PRIV
    elif xkey_header in BITCOIN_HEADERS:
        head = BITCOIN_HEADER_PRIV
    else:
        raise Exception("Unknown xkey header: '%s'" % xkey_header)

    depth = ord(xkey[4])
    fingerprint = xkey[5:9]
    child_number = xkey[9:13]
    c = xkey[13:13+32]
    if xkey[0:4].encode('hex') == head:
        K_or_k = xkey[13+33:]
    else:
        K_or_k = xkey[13+32:]
    return depth, fingerprint, child_number, c, K_or_k


def get_xkey_name(xkey, testnet=False):
    depth, fingerprint, child_number, c, K = deserialize_xkey(xkey)
    n = int(child_number.encode('hex'), 16)
    if n & BIP32_PRIME:
        child_id = "%d'"%(n - BIP32_PRIME)
    else:
        child_id = "%d"%n
    if depth == 0:
        return ''
    elif depth == 1:
        return child_id
    else:
        raise BaseException("xpub depth error")


def xpub_from_xprv(xprv, testnet=False):
    depth, fingerprint, child_number, c, k = deserialize_xkey(xprv)
    K, cK = get_pubkeys_from_secret(k)
    header_pub, _  = _get_headers(testnet)
    xpub = header_pub.decode('hex') + chr(depth) + fingerprint + child_number + c + cK
    return EncodeBase58Check(xpub)


def bip32_root(seed, testnet=False):
    header_pub, header_priv = _get_headers(testnet)
    I = hmac.new("Bitcoin seed", seed, hashlib.sha512).digest()
    master_k = I[0:32]
    master_c = I[32:]
    K, cK = get_pubkeys_from_secret(master_k)
    xprv = (header_priv + "00" + "00000000" + "00000000").decode("hex") + master_c + chr(0) + master_k
    xpub = (header_pub + "00" + "00000000" + "00000000").decode("hex") + master_c + cK
    return EncodeBase58Check(xprv), EncodeBase58Check(xpub)


def xpub_from_pubkey(cK, testnet=False):
    header_pub, header_priv = _get_headers(testnet)
    assert cK[0] in ['\x02','\x03']
    master_c = chr(0)*32
    xpub = (header_pub + "00" + "00000000" + "00000000").decode("hex") + master_c + cK
    return EncodeBase58Check(xpub)


def bip32_private_derivation(xprv, branch, sequence, testnet=False):
    assert sequence.startswith(branch)
    if branch == sequence:
        return xprv, xpub_from_xprv(xprv, testnet)
    header_pub, header_priv = _get_headers(testnet)
    depth, fingerprint, child_number, c, k = deserialize_xkey(xprv)
    sequence = sequence[len(branch):]
    for n in sequence.split('/'):
        if n == '': continue
        i = int(n[:-1]) + BIP32_PRIME if n[-1] == "'" else int(n)
        parent_k = k
        k, c = CKD_priv(k, c, i)
        depth += 1

    _, parent_cK = get_pubkeys_from_secret(parent_k)
    fingerprint = hash_160(parent_cK)[0:4]
    child_number = ("%08X"%i).decode('hex')
    K, cK = get_pubkeys_from_secret(k)
    xprv = header_priv.decode('hex') + chr(depth) + fingerprint + child_number + c + chr(0) + k
    xpub = header_pub.decode('hex') + chr(depth) + fingerprint + child_number + c + cK
    return EncodeBase58Check(xprv), EncodeBase58Check(xpub)


def bip32_public_derivation(xpub, branch, sequence, testnet=False):
    header_pub, _ = _get_headers(testnet)
    depth, fingerprint, child_number, c, cK = deserialize_xkey(xpub)
    assert sequence.startswith(branch)
    sequence = sequence[len(branch):]
    for n in sequence.split('/'):
        if n == '': continue
        i = int(n)
        parent_cK = cK
        cK, c = CKD_pub(cK, c, i)
        depth += 1

    fingerprint = hash_160(parent_cK)[0:4]
    child_number = ("%08X"%i).decode('hex')
    xpub = header_pub.decode('hex') + chr(depth) + fingerprint + child_number + c + cK
    return EncodeBase58Check(xpub)


def bip32_private_key(sequence, k, chain):
    for i in sequence:
        k, chain = CKD_priv(k, chain, i)
    return SecretToASecret(k, True)


def xkeys_from_seed(seed, passphrase, derivation):
    from mnemonic import Mnemonic
    xprv, xpub = bip32_root(Mnemonic.mnemonic_to_seed(seed, passphrase))
    xprv, xpub = bip32_private_derivation(xprv, "m/", derivation)
    return xprv, xpub
