#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@ecdsa.org
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
import util
from bitcoin import *

MAX_TARGET = 0x000fffffff000000000000000000000000000000000000000000000000000000 #0x00000000FFFF0000000000000000000000000000000000000000000000000000 qpc
NULL_HASH = '0000000000000000000000000000000000000000000000000000000000000000'

class Blockchain(util.PrintError):
    '''Manages blockchain headers and their verification'''
    def __init__(self, config, network):
        self.config = config
        self.network = network
        self.headers_url = ''#"https://headers.electrum.org/blockchain_headers" #qpc header_url
        self.local_height = 0
        self.set_local_height()

    def height(self):
        return self.local_height

    def init(self):
        self.init_headers_file()
        self.set_local_height()
        self.print_error("%d blocks" % self.local_height)

    def verify_header(self, header, prev_header, bits, target):
        prev_hash = self.hash_header(prev_header)
        assert prev_hash == header.get('prev_block_hash'), "prev hash mismatch: %s vs %s" % (prev_hash, header.get('prev_block_hash'))
        assert bits == header.get('bits'), "bits mismatch: %s vs %s" % (bits, header.get('bits'))
        _hash = self.hash_header(header)
        assert int('0x' + _hash, 16) <= target, "insufficient proof of work: %s vs target %s" % (int('0x' + _hash, 16), target)

    def verify_chain(self, chain):
        # first_header = chain[0]
        # prev_header = self.read_header(first_header.get('block_height') - 1)
        # for header in chain:
        #     height = header.get('block_height')
        #     bits, target = self.get_target(height / 96, chain)#qpc
        #     self.verify_header(header, prev_header, bits, target)
        #     prev_header = header #qpc
        first_header = chain[0]
        height = first_header['block_height']
        prev_header = self.read_header(height - 1)
        for header in chain:
            height = header['block_height']
            if self.read_header(height) is not None:
                bits, target = self.get_target(height, prev_header, header)
                self.verify_header(header, prev_header, bits, target)
            prev_header = header

    def verify_chunk(self, index, data):
        prev_header = None
        if index != 0:
            prev_header = self.read_header(index * 96 - 1)
        for i in range(96):
            try:
                raw_header = data[i * 140:(i + 1) * 140]
                header = self.deserialize_header(raw_header)
                bits, target = self.get_target(index * 96 + i, prev_header, header)
                if header is not None:
                    self.verify_header(header, prev_header, bits, target)
                prev_header = header
            except BaseException ,ex:
                print 'verify_chunk_err: index:',index,'i:',i
                print ex

    def serialize_header(self, res):
        s= ''
        try:
            s = int_to_hex(res.get('version'), 4) \
                + rev_hex(self.get_block_hash(res)) \
                + rev_hex(res.get('merkle_root')) \
                + rev_hex(res.get('claim_trie_root')) \
                + int_to_hex(int(res.get('timestamp')), 4) \
                + int_to_hex(int(res.get('bits')), 4) \
                + rev_hex(res.get('nonce'))
        except Exception,e:
            print e
        return s

    def get_block_hash(self, header):
        block_hash = header.get('prev_block_hash')
        if block_hash:
            return block_hash
        else:
            assert header.get('block_height') == 0
            return NULL_HASH

    def deserialize_header(self, s):
        h = {}
        h['version'] = hex_to_int(s[0:4])
        h['prev_block_hash'] = hash_encode(s[4:36])
        h['merkle_root'] = hash_encode(s[36:68])
        h['claim_trie_root'] = hash_encode(s[68:100])
        h['timestamp'] = hex_to_int(s[100:104])
        h['bits'] = hex_to_int(s[104:108])
        h['nonce'] = hash_encode(s[108:140])
        return h

    def hash_header(self, header):
        if header is None:
            return '0' * 64
        return hash_encode(Hash_Header(self.serialize_header(header).decode('hex')))

    def path(self):
        return util.get_headers_path(self.config)

    def init_headers_file(self):
        filename = self.path()
        if os.path.exists(filename):
            return
        try:
            import urllib, socket
            socket.setdefaulttimeout(30)
            self.print_error("downloading ", self.headers_url)
            urllib.urlretrieve(self.headers_url, filename)
            self.print_error("done.")
        except Exception:
            self.print_error("download failed. creating file", filename)
            open(filename, 'wb+').close()

    def save_chunk(self, index, chunk):
        filename = self.path()
        f = open(filename, 'rb+')
        f.seek(index * 96 * 140) #qpc
        h = f.write(chunk)
        f.close()
        self.set_local_height()

    def save_header(self, header):
        data = self.serialize_header(header).decode('hex')
        assert len(data) == 140#qpc
        height = header.get('block_height')
        filename = self.path()
        f = open(filename, 'rb+')
        f.seek(height * 140)#qpc
        h = f.write(data)
        f.close()
        self.set_local_height()

    def set_local_height(self):
        name = self.path()
        if os.path.exists(name):
            h = os.path.getsize(name)/140 - 1#qpc
            if self.local_height != h:
                self.local_height = h

    def read_header(self, block_height):
        name = self.path()
        if os.path.exists(name):
            f = open(name, 'rb')
            f.seek(block_height * 140)#qpc
            h = f.read(140)#qpc
            f.close()
            if len(h) == 140:#qpc
                h = self.deserialize_header(h)
                return h

    def get_target(self, index,first, last, chain='main'):
        if index == 0:
            return 0x1f0fffff, MAX_TARGET #qpc
        # first = self.read_header((index-1) * 96) #qpc
        # last = self.read_header(index*96 - 1) #qpc
        # if last is None:
        #     for h in chain:
        #         if h.get('block_height') == index*96 - 1: #qpc
        #             last = h
        # assert last is not None
        # # bits to target
        # bits = last.get('bits')
        # bitsN = (bits >> 24) & 0xff
        # assert bitsN >= 0x03 and bitsN <= 0x1d, "First part of bits should be in [0x03, 0x1d]"
        # bitsBase = bits & 0xffffff
        # assert bitsBase >= 0x8000 and bitsBase <= 0x7fffff, "Second part of bits should be in [0x8000, 0x7fffff]"
        # target = bitsBase << (8 * (bitsN-3))
        # # new target
        # nActualTimespan = last.get('timestamp') - first.get('timestamp')
        # nTargetTimespan = 14 * 24 * 60 * 60
        # nActualTimespan = max(nActualTimespan, nTargetTimespan / 4)
        # nActualTimespan = min(nActualTimespan, nTargetTimespan * 4)
        # new_target = min(MAX_TARGET, (target*nActualTimespan) / nTargetTimespan)
        # # convert new target to bits
        # c = ("%064x" % new_target)[2:]
        # while c[:2] == '00' and len(c) > 6:
        #     c = c[2:]
        # bitsN, bitsBase = len(c) / 2, int('0x' + c[:6], 16)
        # if bitsBase >= 0x800000:
        #     bitsN += 1
        #     bitsBase >>= 8
        # new_bits = bitsN << 24 | bitsBase
        # return new_bits, bitsBase << (8 * (bitsN-3)) #qpc
        assert last is not None, "Last shouldn't be none"
        # bits to target
        bits = last.get('bits')
        # print_error("Last bits: ", bits)
        self.check_bits(bits)

        # new target
        nActualTimespan = last.get('timestamp') - first.get('timestamp')
        nTargetTimespan = 150  #150
        nModulatedTimespan = nTargetTimespan - (nActualTimespan - nTargetTimespan) / 8
        nMinTimespan = nTargetTimespan - (nTargetTimespan / 8)
        nMaxTimespan = nTargetTimespan + (nTargetTimespan / 2)
        if nModulatedTimespan < nMinTimespan:
            nModulatedTimespan = nMinTimespan
        elif nModulatedTimespan > nMaxTimespan:
            nModulatedTimespan = nMaxTimespan

        bnOld = ArithUint256.SetCompact(bits)
        bnNew = bnOld * nModulatedTimespan

        bnNew /= nModulatedTimespan
        if bnNew > MAX_TARGET:
            bnNew = ArithUint256(MAX_TARGET)
        return bnNew.GetCompact(), bnNew._value

    def connect_header(self, chain, header):
        '''Builds a header chain until it connects.  Returns True if it has
        successfully connected, False if verification failed, otherwise the
        height of the next header needed.'''
        # chain.append(header)  # Ordered by decreasing height
        # previous_height = header['block_height'] - 1
        # previous_header = self.read_header(previous_height)
        #
        # # Missing header, request it
        # if not previous_header:
        #     return previous_height
        #
        # # Does it connect to my chain?
        # prev_hash = self.hash_header(previous_header)
        # if prev_hash != header.get('prev_block_hash'):
        #     self.print_error("reorg")
        #     return previous_height
        #
        # # The chain is complete.  Reverse to order by increasing height
        # chain.reverse()
        # try:
        #     self.verify_chain(chain)
        #     self.print_error("new height:", previous_height + len(chain))
        #     for header in chain:
        #         self.save_header(header)
        #     return True
        # except BaseException as e:
        #     self.print_error(str(e))
        #     return False #qpc
        chain.append(header)  # Ordered by decreasing height
        height = header['block_height']
        if height > 0 and self.need_previous(header):
            return height - 1
        # The chain is complete so we can save it
        return self.save_chain(chain, height)
    def need_previous(self, header):
        """Return True if we're missing the block before the one we just got"""
        previous_height = header['block_height'] - 1
        previous_header = self.read_header(previous_height)
        # Missing header, request it
        if not previous_header:
            return True
        # Does it connect to my chain?
        prev_hash = self.hash_header(previous_header)
        if prev_hash != header.get('prev_block_hash'):
            return True

    def save_chain(self, chain, height):
        # Reverse to order by increasing height
        chain.reverse()
        try:
            self.verify_chain(chain)
            print "connected at height: %i", height
            for header in chain:
                self.save_header(header)
            return True
        except BaseException as e:
            print "error saving chain"
            return False

    def connect_chunk(self, idx, hexdata):
        try:
            data = hexdata.decode('hex')
            self.verify_chunk(idx, data)
            self.print_error("validated chunk %d" % idx)
            self.save_chunk(idx, data)
            return idx + 1
        except BaseException as e:
            self.print_error('verify_chunk failed', str(e))
            return idx - 1

    def check_bits(self, bits):
        bitsN = (bits >> 24) & 0xff
        assert 0x03 <= bitsN <= 0x1f, \
            "First part of bits should be in [0x03, 0x1d], but it was {}".format(hex(bitsN))
        bitsBase = bits & 0xffffff
        assert 0x8000 <= bitsBase <= 0x7fffff, \
            "Second part of bits should be in [0x8000, 0x7fffff] but it was {}".format(bitsBase)

class ArithUint256(object):
    def __init__(self, value):
        self._value = value

    def __str__(self):
        return hex(self._value)

    @staticmethod
    def fromCompact(nCompact):
        """Convert a compact representation into its value"""
        nSize = nCompact >> 24
        # the lower 23 bits
        nWord = nCompact & 0x007fffff
        if nSize <= 3:
            return nWord >> 8 * (3 - nSize)
        else:
            return nWord << 8 * (nSize - 3)

    @classmethod
    def SetCompact(cls, nCompact):
        return cls(ArithUint256.fromCompact(nCompact))

    def bits(self):
        """Returns the position of the highest bit set plus one."""
        bn = bin(self._value)[2:]
        for i, d in enumerate(bn):
            if d:
                return (len(bn) - i) + 1
        return 0

    def GetLow64(self):
        return self._value & 0xffffffffffffffff

    def GetCompact(self):
        """Convert a value into its compact representation"""
        nSize = (self.bits() + 7) // 8
        nCompact = 0
        if nSize <= 3:
            nCompact = self.GetLow64() << 8 * (3 - nSize)
        else:
            bn = ArithUint256(self._value >> 8 * (nSize - 3))
            nCompact = bn.GetLow64()
        # The 0x00800000 bit denotes the sign.
        # Thus, if it is already set, divide the mantissa by 256 and increase the exponent.
        if nCompact & 0x00800000:
            nCompact >>= 8
            nSize += 1
        assert (nCompact & ~0x007fffff) == 0
        assert nSize < 256
        nCompact |= nSize << 24
        return nCompact

    def __mul__(self, x):
        # Take the mod because we are limited to an unsigned 256 bit number
        return ArithUint256((self._value * x) % 2 ** 256)

    def __idiv__(self, x):
        self._value = (self._value // x)
        return self

    def __gt__(self, x):
        return self._value > x