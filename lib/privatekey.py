# -*- coding: utf-8 -*-
"""
    pybitcoin
    ~~~~~

    :copyright: (c) 2014 by Halfmoon Labs
    :license: MIT, see LICENSE for more details.
"""

import os
import sys
import json
import hashlib
import ecdsa
import binascii
from utilitybelt import dev_random_entropy,change_charset

# from .publickey import BitcoinPublicKey, PUBKEY_MAGIC_BYTE
# from .passphrases import create_passphrase
import re

P = 2**256 - 2**32 - 977

N = 115792089237316195423570985008687907852837564279074904382605163141518161494337
A = 0
B = 7
Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424
G = (Gx, Gy)

HEX_KEYSPACE = "0123456789abcdef"
B58_KEYSPACE = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

if sys.version_info.major == 2:
    string_types = (str, unicode)
    string_or_bytes_types = string_types
    int_types = (int, float, long)

    # Base switching
    code_strings = {
        2: '01',
        10: '0123456789',
        16: '0123456789abcdef',
        32: 'abcdefghijklmnopqrstuvwxyz234567',
        58: '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz',
        256: ''.join([chr(x) for x in range(256)])
    }

    def bin_dbl_sha256(s):
        bytes_to_hash = from_string_to_bytes(s)
        return hashlib.sha256(hashlib.sha256(bytes_to_hash).digest()).digest()

    def lpad(msg, symbol, length):
        if len(msg) >= length:
            return msg
        return symbol * (length - len(msg)) + msg

    def get_code_string(base):
        if base in code_strings:
            return code_strings[base]
        else:
            raise ValueError("Invalid base!")

    def changebase(string, frm, to, minlen=0):
        if frm == to:
            return lpad(string, get_code_string(frm)[0], minlen)
        return encode(decode(string, frm), to, minlen)

    def bin_to_b58check(inp, magicbyte=0):
        inp_fmtd = chr(int(magicbyte)) + inp
        leadingzbytes = len(re.match('^\x00*', inp_fmtd).group(0))
        checksum = bin_dbl_sha256(inp_fmtd)[:4]
        return '1' * leadingzbytes + changebase(inp_fmtd+checksum, 256, 58)

    def bytes_to_hex_string(b):
        return b.encode('hex')

    def safe_from_hex(s):
        return s.decode('hex')

    def from_int_representation_to_bytes(a):
        return str(a)

    def from_int_to_byte(a):
        return chr(a)

    def from_byte_to_int(a):
        return ord(a)

    def from_bytes_to_string(s):
        return s

    def from_string_to_bytes(a):
        return a

    def safe_hexlify(a):
        return binascii.hexlify(a)

    def encode(val, base, minlen=0):
        base, minlen = int(base), int(minlen)
        code_string = get_code_string(base)
        result = ""
        while val > 0:
            result = code_string[val % base] + result
            val //= base
        return code_string[0] * max(minlen - len(result), 0) + result

    def decode(string, base):
        base = int(base)
        code_string = get_code_string(base)
        result = 0
        if base == 16:
            string = string.lower()
        while len(string) > 0:
            result *= base
            result += code_string.find(string[0])
            string = string[1:]
        return result

    def random_string(x):
        return os.urandom(x)

def bin_sha256(bin_s):
    return hashlib.sha256(bin_s).digest()


def bin_checksum(bin_s):
    """ Takes in a binary string and returns a checksum. """
    return bin_sha256(bin_sha256(bin_s))[:4]

def b58check_encode(bin_s, version_byte=0):
    """ Takes in a binary string and converts it to a base 58 check string. """
    # append the version byte to the beginning
    bin_s = chr(int(version_byte)) + bin_s
    # calculate the number of leading zeros
    num_leading_zeros = len(re.match(r'^\x00*', bin_s).group(0))
    # add in the checksum add the end
    bin_s = bin_s + bin_checksum(bin_s)
    # convert from b2 to b16
    hex_s = binascii.hexlify(bin_s)
    # convert from b16 to b58
    b58_s = change_charset(hex_s, HEX_KEYSPACE, B58_KEYSPACE)

    return B58_KEYSPACE[0] * num_leading_zeros + b58_s


def b58check_unpack(b58_s):
    """ Takes in a base 58 check string and returns: the version byte, the
        original encoded binary string, and the checksum.
    """
    num_leading_zeros = len(re.match(r'^1*', b58_s).group(0))
    # convert from b58 to b16
    hex_s = change_charset(b58_s, B58_KEYSPACE, HEX_KEYSPACE)
    # if an odd number of hex characters are present, add a zero to the front
    if len(hex_s) % 2 == 1:
        hex_s = "0" + hex_s
    # convert from b16 to b2
    bin_s = binascii.unhexlify(hex_s)
    # add in the leading zeros
    bin_s = '\x00' * num_leading_zeros + bin_s
    # make sure the newly calculated checksum equals the embedded checksum
    newly_calculated_checksum = bin_checksum(bin_s[:-4])
    embedded_checksum = bin_s[-4:]
    if not (newly_calculated_checksum == embedded_checksum):
        raise ValueError('b58check value has an invalid checksum')
    # return values
    version_byte = bin_s[:1]
    encoded_value = bin_s[1:-4]
    checksum = bin_s[-4:]
    return version_byte, encoded_value, checksum


def b58check_decode(b58_s):
    """ Takes in a base 58 check string and returns the original encoded binary
        string.
    """
    version_byte, encoded_value, checksum = b58check_unpack(b58_s)
    return encoded_value


def b58check_version_byte(b58_s):
    """ Takes in a base 58 check string and returns the version byte as an
        integer. """
    version_byte, encoded_value, checksum = b58check_unpack(b58_s)
    return ord(version_byte)


def is_b58check(b58_s):
    version_byte, binary_s, checksum = b58check_unpack(b58_s)
    return (b58_s == b58check_encode(
        binary_s, version_byte=ord(version_byte)))

def b58check_to_bin(inp):
    leadingzbytes = len(re.match('^1*', inp).group(0))
    data = b'\x00' * leadingzbytes + changebase(inp, 58, 256)
    assert bin_dbl_sha256(data[:-4])[:4] == data[-4:]
    return data[1:-4]


def get_privkey_format(priv):
    if isinstance(priv, int_types): return 'decimal'
    elif len(priv) == 32: return 'bin'
    elif len(priv) == 33: return 'bin_compressed'
    elif len(priv) == 64: return 'hex'
    elif len(priv) == 66: return 'hex_compressed'
    else:
        bin_p = b58check_to_bin(priv)
        if len(bin_p) == 32: return 'wif'
        elif len(bin_p) == 33: return 'wif_compressed'
        else: raise Exception("WIF does not represent privkey")

def decode_privkey(priv,formt=None):
    if not formt: formt = get_privkey_format(priv)
    if formt == 'decimal': return priv
    elif formt == 'bin': return decode(priv, 256)
    elif formt == 'bin_compressed': return decode(priv[:32], 256)
    elif formt == 'hex': return decode(priv, 16)
    elif formt == 'hex_compressed': return decode(priv[:64], 16)
    elif formt == 'wif': return decode(b58check_to_bin(priv),256)
    elif formt == 'wif_compressed':
        return decode(b58check_to_bin(priv)[:32],256)
    else: raise Exception("WIF does not represent privkey")


def encode_privkey(priv, formt, vbyte=0):
    if not isinstance(priv, int_types):
        return encode_privkey(decode_privkey(priv), formt, vbyte)
    if formt == 'decimal': return priv
    elif formt == 'bin': return encode(priv, 256, 32)
    elif formt == 'bin_compressed': return encode(priv, 256, 32)+b'\x01'
    elif formt == 'hex': return encode(priv, 16, 64)
    elif formt == 'hex_compressed': return encode(priv, 16, 64)+'01'
    elif formt == 'wif':
        return bin_to_b58check(encode(priv, 256, 32), 128+int(vbyte))
    elif formt == 'wif_compressed':
        return bin_to_b58check(encode(priv, 256, 32)+b'\x01', 128+int(vbyte))
    else: raise Exception("Invalid format!")

def is_secret_exponent(val, curve_order):
    return (isinstance(val, (int, long)) and val >= 1 and val < curve_order)

def random_secret_exponent(curve_order):
    """ Generates a random secret exponent. """
    # run a rejection sampling algorithm to ensure the random int is less
    # than the curve order
    while True:
        # generate a random 256 bit hex string
        random_hex = binascii.hexlify(dev_random_entropy(32))
        random_int = int(random_hex, 16)
        if random_int >= 1 and random_int < curve_order:
            break
    return random_int



def encode_pubkey(pub, formt):
    if not isinstance(pub, (tuple, list)):
        pub = decode_pubkey(pub)
    if formt == 'decimal': return pub
    elif formt == 'bin': return b'\x04' + encode(pub[0], 256, 32) + encode(pub[1], 256, 32)
    elif formt == 'bin_compressed':
        return from_int_to_byte(2+(pub[1] % 2)) + encode(pub[0], 256, 32)
    elif formt == 'hex': return '04' + encode(pub[0], 16, 64) + encode(pub[1], 16, 64)
    elif formt == 'hex_compressed':
        return '0'+str(2+(pub[1] % 2)) + encode(pub[0], 16, 64)
    elif formt == 'bin_electrum': return encode(pub[0], 256, 32) + encode(pub[1], 256, 32)
    elif formt == 'hex_electrum': return encode(pub[0], 16, 64) + encode(pub[1], 16, 64)
    else: raise Exception("Invalid format!")


def decode_pubkey(pub, formt=None):
    if not formt: formt = get_pubkey_format(pub)
    if formt == 'decimal': return pub
    elif formt == 'bin': return (decode(pub[1:33], 256), decode(pub[33:65], 256))
    elif formt == 'bin_compressed':
        x = decode(pub[1:33], 256)
        beta = pow(int(x*x*x+A*x+B), int((P+1)//4), int(P))
        y = (P-beta) if ((beta + from_byte_to_int(pub[0])) % 2) else beta
        return (x, y)
    elif formt == 'hex': return (decode(pub[2:66], 16), decode(pub[66:130], 16))
    elif formt == 'hex_compressed':
        return decode_pubkey(safe_from_hex(pub), 'bin_compressed')
    elif formt == 'bin_electrum':
        return (decode(pub[:32], 256), decode(pub[32:64], 256))
    elif formt == 'hex_electrum':
        return (decode(pub[:64], 16), decode(pub[64:128], 16))
    else: raise Exception("Invalid format!")

def get_pubkey_format(pub):
    two = '\x02'
    three = '\x03'
    four = '\x04'
    if isinstance(pub, (tuple, list)): return 'decimal'
    elif len(pub) == 65 and pub[0] == four: return 'bin'
    elif len(pub) == 130 and pub[0:2] == '04': return 'hex'
    elif len(pub) == 33 and pub[0] in [two, three]: return 'bin_compressed'
    elif len(pub) == 66 and pub[0:2] in ['02', '03']: return 'hex_compressed'
    elif len(pub) == 64: return 'bin_electrum'
    elif len(pub) == 128: return 'hex_electrum'
    else: raise Exception("Pubkey not in recognized format")

def compress(pubkey):
    f = get_pubkey_format(pubkey)
    if 'compressed' in f: return pubkey
    elif f == 'bin': return encode_pubkey(decode_pubkey(pubkey, f), 'bin_compressed')
    elif f == 'hex' or f == 'decimal':
        return encode_pubkey(decode_pubkey(pubkey, f), 'hex_compressed')

class BitcoinPrivateKey():
    _curve = ecdsa.curves.SECP256k1
    _hash_function = hashlib.sha256
    _pubkeyhash_version_byte = 0

    @classmethod
    def wif_version_byte(cls):
        if hasattr(cls, '_wif_version_byte'):
            return cls._wif_version_byte
        return (cls._pubkeyhash_version_byte + 128) % 256

    def __init__(self, private_key=None, compressed=False):
        """ Takes in a private key/secret exponent.
        """
        self._compressed = compressed
        if not private_key:
            secret_exponent = random_secret_exponent(self._curve.order)
        else:
            secret_exponent = encode_privkey(private_key, 'decimal')
            if get_privkey_format(private_key).endswith('compressed'):
                self._compressed = True

        # make sure that: 1 <= secret_exponent < curve_order
        if not is_secret_exponent(secret_exponent, self._curve.order):
            raise Exception

        self._ecdsa_private_key = ecdsa.keys.SigningKey.from_secret_exponent(
            secret_exponent, self._curve, self._hash_function
        )

    # @classmethod
    # def from_passphrase(cls, passphrase=None):
    #     """ Create keypair from a passphrase input (a brain wallet keypair)."""
    #     if not passphrase:
    #         # run a rejection sampling algorithm to ensure the private key is
    #         # less than the curve order
    #         while True:
    #             passphrase = create_passphrase(bits_of_entropy=160)
    #             hex_private_key = hashlib.sha256(passphrase).hexdigest()
    #             if int(hex_private_key, 16) < cls._curve.order:
    #                 break
    #     else:
    #         hex_private_key = hashlib.sha256(passphrase).hexdigest()
    #         if not (int(hex_private_key, 16) < cls._curve.order):
    #             raise ValueError(_errors["CURVE_ORDER_EXCEEDED"])
    #
    #     keypair = cls(hex_private_key)
    #     keypair._passphrase = passphrase
    #     return keypair

    def to_bin(self):
        if self._compressed:
            return encode_privkey(
                self._ecdsa_private_key.to_string(), 'bin_compressed')
        else:
            return self._ecdsa_private_key.to_string()

    def to_hex(self):
        if self._compressed:
            return encode_privkey(
                self._ecdsa_private_key.to_string(), 'hex_compressed')
        else:
            return binascii.hexlify(self.to_bin())

    def to_wif(self):
        if self._compressed:
            return encode_privkey(
                self._ecdsa_private_key.to_string(), 'wif_compressed')
        else:
            return b58check_encode(
                self.to_bin(), version_byte=self.wif_version_byte())

    def to_pem(self):
        return self._ecdsa_private_key.to_pem()

    def to_der(self):
        return binascii.hexlify(self._ecdsa_private_key.to_der())

    def public_key(self):
        # lazily calculate and set the public key
        if not hasattr(self, '_public_key'):
            ecdsa_public_key = self._ecdsa_private_key.get_verifying_key()

            bin_public_key_string = PUBKEY_MAGIC_BYTE + \
                ecdsa_public_key.to_string()

            if self._compressed:
                bin_public_key_string = compress(bin_public_key_string)

            # create the public key object from the public key string
            self._public_key = BitcoinPublicKey(
                bin_public_key_string,
                version_byte=self._pubkeyhash_version_byte)

        # return the public key object
        return self._public_key

    def passphrase(self):
        if hasattr(self, '_passphrase'):
            return self._passphrase
        else:
            raise Exception


class LitecoinPrivateKey(BitcoinPrivateKey):
    _pubkeyhash_version_byte = 48


class NamecoinPrivateKey(BitcoinPrivateKey):
    _pubkeyhash_version_byte = 52


# -*- coding: utf-8 -*-
"""
    pybitcoin
    ~~~~~

    :copyright: (c) 2014 by Halfmoon Labs
    :license: MIT, see LICENSE for more details.
"""

import os
import json
import hashlib
import ecdsa
from binascii import hexlify, unhexlify
from ecdsa.keys import VerifyingKey
# from bitcoin import decompress, compress, pubkey_to_address
from utilitybelt import is_hex

# from .errors import _errors
# from .hash import bin_hash160 as get_bin_hash160
# from .formatcheck import is_hex_ecdsa_pubkey, is_binary_ecdsa_pubkey
# from .b58check import b58check_encode
# from .address import bin_hash160_to_address

PUBKEY_MAGIC_BYTE = '\x04'


def bin_hash160(string):
    intermed = hashlib.sha256(string).digest()
    digest = ''
    try:
        digest = hashlib.new('ripemd160', intermed).digest()
    except:
        raise  Exception
    return digest

def pubkey_to_address(pubkey, magicbyte=0):
    if isinstance(pubkey, (list, tuple)):
        pubkey = encode_pubkey(pubkey, 'bin')
    if len(pubkey) in [66, 130]:
        return bin_to_b58check(
            bin_hash160(binascii.unhexlify(pubkey)), magicbyte)
    return bin_to_b58check(bin_hash160(pubkey), magicbyte)

pubtoaddr = pubkey_to_address

def decompress(pubkey):
    f = get_pubkey_format(pubkey)
    if 'compressed' not in f: return pubkey
    elif f == 'bin_compressed': return encode_pubkey(decode_pubkey(pubkey, f), 'bin')
    elif f == 'hex_compressed' or f == 'decimal':
        return encode_pubkey(decode_pubkey(pubkey, f), 'hex')

class CharEncoding():
    hex = 16
    bin = 256


class PubkeyType():
    ecdsa = 1
    uncompressed = 2
    compressed = 3


def get_public_key_format(public_key_string):
    if not isinstance(public_key_string, str):
        raise ValueError('Public key must be a string.')

    if len(public_key_string) == 64:
        return CharEncoding.bin, PubkeyType.ecdsa

    if (len(public_key_string) == 65 and
            public_key_string[0] == PUBKEY_MAGIC_BYTE):
        return CharEncoding.bin, PubkeyType.uncompressed

    if len(public_key_string) == 33:
        return CharEncoding.bin, PubkeyType.compressed

    if is_hex(public_key_string):
        if len(public_key_string) == 128:
            return CharEncoding.hex, PubkeyType.ecdsa

        if (len(public_key_string) == 130 and
                public_key_string[0:2] == hexlify(PUBKEY_MAGIC_BYTE)):
            return CharEncoding.hex, PubkeyType.uncompressed

        if len(public_key_string) == 66:
            return CharEncoding.hex, PubkeyType.compressed

    raise Exception


def extract_bin_ecdsa_pubkey(public_key):
    key_charencoding, key_type = get_public_key_format(public_key)

    if key_charencoding == CharEncoding.hex:
        bin_public_key = unhexlify(public_key)
    elif key_charencoding == CharEncoding.bin:
        bin_public_key = public_key
    else:
        raise Exception

    if key_type == PubkeyType.ecdsa:
        return bin_public_key
    elif key_type == PubkeyType.uncompressed:
        return bin_public_key[1:]
    elif key_type == PubkeyType.compressed:
        return decompress(bin_public_key)[1:]
    else:
        raise Exception


def extract_bin_bitcoin_pubkey(public_key):
    key_charencoding, key_type = get_public_key_format(public_key)

    if key_charencoding == CharEncoding.hex:
        bin_public_key = unhexlify(public_key)
    elif key_charencoding == CharEncoding.bin:
        bin_public_key = public_key
    else:
        raise Exception

    if key_type == PubkeyType.ecdsa:
        return PUBKEY_MAGIC_BYTE + bin_public_key
    elif key_type == PubkeyType.uncompressed:
        return bin_public_key
    elif key_type == PubkeyType.compressed:
        return bin_public_key
    else:
        raise Exception

def bin_hash160_to_address(bin_hash160, version_byte=0):
    return b58check_encode(bin_hash160, version_byte=version_byte)

def get_bin_hash160(s, hex_format=False):
    """ s is in hex or binary format
    """
    if hex_format and is_hex(s):
        s = unhexlify(s)
    return hashlib.new('ripemd160', bin_sha256(s)).digest()

class BitcoinPublicKey():
    _curve = ecdsa.curves.SECP256k1
    _version_byte = 0

    @classmethod
    def version_byte(cls):
        return cls._version_byte

    def __init__(self, public_key_string, version_byte=None, verify=True):
        """ Takes in a public key in hex format.
        """
        # set the version byte
        if version_byte:
            self._version_byte = version_byte

        self._charencoding, self._type = get_public_key_format(
            public_key_string)

        # extract the binary bitcoin key (compressed/uncompressed w magic byte)
        self._bin_public_key = extract_bin_bitcoin_pubkey(public_key_string)

        # extract the bin ecdsa public key (uncompressed, w/out a magic byte)
        bin_ecdsa_public_key = extract_bin_ecdsa_pubkey(public_key_string)
        if verify:
            try:
                # create the ecdsa key object
                self._ecdsa_public_key = VerifyingKey.from_string(
                    bin_ecdsa_public_key, self._curve)
            except AssertionError as e:
                raise Exception

    def to_bin(self):
        return self._bin_public_key

    def to_hex(self):
        return hexlify(self.to_bin())

    def to_pem(self):
        return self._ecdsa_public_key.to_pem()

    def to_der(self):
        return hexlify(self._ecdsa_public_key.to_der())

    def bin_hash160(self):
        if not hasattr(self, '_bin_hash160'):
            self._bin_hash160 = get_bin_hash160(self.to_bin())
        return self._bin_hash160

    def hash160(self):
        return hexlify(self.bin_hash160())

    def address(self):
        if self._type == PubkeyType.compressed:
            bin_hash160 = get_bin_hash160(compress(self.to_bin()))
            return bin_hash160_to_address(
                bin_hash160, version_byte=self._version_byte)

        return bin_hash160_to_address(self.bin_hash160(),
                                      version_byte=self._version_byte)


class LitecoinPublicKey(BitcoinPublicKey):
    _version_byte = 48


class NamecoinPublicKey(BitcoinPublicKey):
    _version_byte = 52

if __name__ == '__main__':
    private_key = BitcoinPrivateKey()
    pk = private_key.to_wif()
    a =  1