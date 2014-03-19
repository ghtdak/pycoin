# -*- coding: utf-8 -*-
"""
A BIP0032-style hierarchical wallet.

Implement a BIP0032-style hierarchical wallet which can create public
or private wallet keys. Each key can create many child nodes. Each node
has a wallet key and a corresponding private & public key, which can
be used to generate Bitcoin addresses or WIF private keys.

At any stage, the private information can be stripped away, after which
descendants can only produce public keys.

Private keys can also generate "prime" children, which cannot be
generated by the corresponding public keys. This is useful for generating
"change" addresses, for example, which there is no need to share with people
you give public keys to.


The MIT License (MIT)

Copyright (c) 2013 by Richard Kiss

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import binascii
import hashlib
import hmac
import struct
import itertools

from . import ecdsa

from .encoding import public_pair_to_sec, sec_to_public_pair,\
    secret_exponent_to_wif, public_pair_to_bitcoin_address,\
    from_bytes_32, to_bytes_32,\
    public_pair_to_hash160_sec, EncodingError

from .encoding import a2b_hashed_base58, b2a_hashed_base58

PRIVATE_TEST_VERSION = [
    (True, False, "0488ADE4"),
    (False, False, "0488B21E"),
    (True, True, "04358394"),
    (False, True, "043587CF"),
]

# generate lookup and reverse lookup
PRIVATE_TEST__VERSION_LOOKUP = dict((
    (p, t), binascii.unhexlify(v.encode("utf8")))
                                    for p, t, v in PRIVATE_TEST_VERSION)
VERSION__PRIVATE_TEST_LOOKUP = dict((int(v, 16), (p, t))
                                    for p, t, v in PRIVATE_TEST_VERSION)


class PublicPrivateMismatchError(Exception):
    pass


class InvalidKeyGeneratedError(Exception):
    pass


def wallet_iterator_for_wallet_key_path(wallet_key_path):
    subkey_paths = ""
    if "/" in wallet_key_path:
        wallet_key_path, subkey_paths = wallet_key_path.split("/", 1)
    return Wallet.from_wallet_key(wallet_key_path).subkeys_for_path(
        subkey_paths)


class Wallet(object):
    """
    This is a deterministic wallet that complies with BIP0032
    https://en.bitcoin.it/wiki/BIP_0032
    """

    @classmethod
    def from_master_secret(class_, master_secret, is_test=False):
        """Generate a Wallet from a master password."""
        I64 = hmac.HMAC(key=b"Bitcoin seed",
                        msg=master_secret,
                        digestmod=hashlib.sha512).digest()
        return class_(is_private=True,
                      is_test=is_test,
                      chain_code=I64[32:],
                      secret_exponent_bytes=I64[:32])

    @classmethod
    def from_wallet_key(class_, b58_str):
        """Generate a Wallet from a base58 string in a standard way."""
        data = a2b_hashed_base58(b58_str)
        header = struct.unpack(">L", data[:4])[0]
        if header not in VERSION__PRIVATE_TEST_LOOKUP:
            raise EncodingError("bad wallet key header")
        is_private, is_test = VERSION__PRIVATE_TEST_LOOKUP.get(struct.unpack(
            ">L", data[:4])[0])
        parent_fingerprint, child_number = struct.unpack(">4sL", data[5:13])

        d = dict(is_private=is_private,
                 is_test=is_test,
                 chain_code=data[13:45],
                 depth=ord(data[4:5]),
                 parent_fingerprint=parent_fingerprint,
                 child_number=child_number)

        if is_private:
            if data[45:46] != b'\0':
                raise EncodingError("private key encoded wrong")
            d["secret_exponent_bytes"] = data[46:]
        else:
            d["public_pair"] = sec_to_public_pair(data[45:])

        return class_(**d)

    def __init__(self,
                 is_private,
                 is_test,
                 chain_code,
                 depth=0,
                 parent_fingerprint=b'\0\0\0\0',
                 child_number=0,
                 secret_exponent_bytes=None,
                 public_pair=None):
        """Don't use this. Use a classmethod to generate from a string instead."""
        if is_private:
            if public_pair:
                raise PublicPrivateMismatchError(
                    "can't include public_pair for private key")
        elif secret_exponent_bytes:
            raise PublicPrivateMismatchError(
                "can't include secret_exponent_bytes for public key")
        self.is_private = is_private
        self.is_test = is_test
        if is_private:
            if len(secret_exponent_bytes) != 32:
                raise EncodingError("private key encoding wrong length")
            self.secret_exponent_bytes = secret_exponent_bytes
            self.secret_exponent = from_bytes_32(self.secret_exponent_bytes)
            if self.secret_exponent > ecdsa.generator_secp256k1.order():
                raise InvalidKeyGeneratedError(
                    "this key would produce an invalid secret exponent; please skip it")
            self.public_pair = ecdsa.public_pair_for_secret_exponent(
                ecdsa.generator_secp256k1, self.secret_exponent)
        else:
            self.public_pair = public_pair
        # validate public_pair is on the curve
        if not ecdsa.is_public_pair_valid(ecdsa.generator_secp256k1,
                                          self.public_pair):
            raise InvalidKeyGeneratedError(
                "this key would produce an invalid public pair; please skip it")
        if not isinstance(chain_code, bytes):
            raise ValueError("chain code must be bytes")
        if len(chain_code) != 32:
            raise EncodingError("chain code wrong length")
        self.chain_code = chain_code
        self.depth = depth
        if len(parent_fingerprint) != 4:
            raise EncodingError("parent_fingerprint wrong length")
        self.parent_fingerprint = parent_fingerprint
        self.child_number = child_number
        self.subkey_cache = dict()

    def serialize(self, as_private=None):
        """Yield a 78-byte binary blob corresponding to this node."""
        if as_private is None:
            as_private = self.is_private
        if not self.is_private and as_private:
            raise PublicPrivateMismatchError("public key has no private parts")

        ba = bytearray(PRIVATE_TEST__VERSION_LOOKUP[(as_private, self.is_test)])
        ba.extend([self.depth])
        ba.extend(self.parent_fingerprint + struct.pack(">L", self.child_number)
                  + self.chain_code)
        if as_private:
            ba += b'\0' + self.secret_exponent_bytes
        else:
            ba += public_pair_to_sec(self.public_pair, compressed=True)
        return bytes(ba)

    def fingerprint(self):
        return public_pair_to_hash160_sec(self.public_pair, compressed=True)[:4]

    def wallet_key(self, as_private=False):
        """Yield a 111-byte string corresponding to this node."""
        return b2a_hashed_base58(self.serialize(as_private=as_private))

    def wif(self, compressed=True):
        """Yield the WIF corresponding to this node."""
        if not self.is_private:
            raise PublicPrivateMismatchError(
                "can't generate WIF for public key")
        return secret_exponent_to_wif(self.secret_exponent,
                                      compressed=compressed,
                                      is_test=self.is_test)

    def bitcoin_address(self, compressed=True):
        """Yield the Bitcoin address corresponding to this node."""
        return public_pair_to_bitcoin_address(self.public_pair,
                                              compressed=compressed,
                                              is_test=self.is_test)

    def public_copy(self):
        """Yield the corresponding public node for this node."""
        return self.__class__(is_private=False,
                              is_test=self.is_test,
                              chain_code=self.chain_code,
                              depth=self.depth,
                              parent_fingerprint=self.parent_fingerprint,
                              child_number=self.child_number,
                              public_pair=self.public_pair)

    def _subkey(self, i, is_prime, as_private):
        """Yield a child node for this node.

        i: the index for this node.
        is_prime: use "private key derivation". That is, the public version
            of this node cannot calculate this child.
        as_private: set to True to get a private subkey.

        Note that setting i<0 uses private key derivation, no matter the
        value for is_prime."""
        if i < 0:
            is_prime = True
            i_as_bytes = struct.pack(">l", i)
        else:
            i &= 0x7fffffff
            if is_prime:
                i |= 0x80000000
            i_as_bytes = struct.pack(">L", i)
        if is_prime:
            if not self.is_private:
                raise PublicPrivateMismatchError(
                    "can't derive a private key from a public key")
            data = b'\0' + self.secret_exponent_bytes + i_as_bytes
        else:
            data = public_pair_to_sec(self.public_pair,
                                      compressed=True) + i_as_bytes
        I64 = hmac.HMAC(key=self.chain_code,
                        msg=data,
                        digestmod=hashlib.sha512).digest()
        I_left_as_exponent = from_bytes_32(I64[:32])
        d = dict(is_private=as_private,
                 is_test=self.is_test,
                 chain_code=I64[32:],
                 depth=self.depth + 1,
                 parent_fingerprint=self.fingerprint(),
                 child_number=i)

        if as_private:
            exponent = (I_left_as_exponent + self.secret_exponent
                       ) % ecdsa.generator_secp256k1.order()
            d["secret_exponent_bytes"] = to_bytes_32(exponent)
        else:
            x, y = self.public_pair
            the_point = I_left_as_exponent * ecdsa.generator_secp256k1 + ecdsa.Point(
                ecdsa.generator_secp256k1.curve(), x, y,
                ecdsa.generator_secp256k1.order())
            d["public_pair"] = the_point.pair()
        return self.__class__(**d)

    def subkey(self, i=0, is_prime=False, as_private=None):
        if as_private is None: as_private = self.is_private
        is_prime = not not is_prime
        as_private = not not as_private
        lookup = (i, is_prime, as_private)
        if lookup not in self.subkey_cache:
            self.subkey_cache[lookup] = self._subkey(i, is_prime, as_private)
        return self.subkey_cache[lookup]

    def subkey_for_path(self, path):
        """
        path: a path of subkeys denoted by numbers and slashes. Use
            p or i<0 for private key derivation. End with .pub to force
            the key public.

        Examples:
            1p/-5/2/1 would call subkey(i=1, is_prime=True).subkey(i=-5).
                subkey(i=2).subkey(i=1) and then yield the private key
            0/0/458.pub would call subkey(i=0).subkey(i=0).subkey(i=458) and
                then yield the public key

        You should choose one of the p or the negative number convention for private key
        derivation and stick with it.
        """
        force_public = (path[-4:] == '.pub')
        if force_public:
            path = path[:-4]
        key = self
        if path:
            invocations = path.split("/")
            for v in invocations:
                is_prime = v[-1] in ("'p")
                if is_prime: v = v[:-1]
                v = int(v)
                key = key.subkey(i=v,
                                 is_prime=is_prime,
                                 as_private=key.is_private)
        if force_public and key.is_private:
            key = key.public_copy()
        return key

    def subkeys_for_path(self, path):
        """
        A generalized form that can return multiple subkeys.
        """
        if path == '':
            yield self
            return

        def range_iterator(the_range):
            for r in the_range.split(","):
                is_prime = r[-1] in "'p"
                if is_prime:
                    r = r[:-1]
                prime_char = "p" if is_prime else ''
                if '-' in r:
                    low, high = [int(x) for x in r.split("-", 1)]
                    for t in range(low, high + 1):
                        yield "%d%s" % (t, prime_char)
                else:
                    yield "%s%s" % (r, prime_char)

        def subkey_iterator(subkey_paths):
            # examples:
            #   0/1p/0-4 => ['0/1p/0', '0/1p/1', '0/1p/2', '0/1p/3', '0/1p/4']
            #   0/2,5,9-11 => ['0/2', '0/5', '0/9', '0/10', '0/11']
            #   3p/2/5/15-20p => ['3p/2/5/15p', '3p/2/5/16p', '3p/2/5/17p', '3p/2/5/18p', '3p/2/5/19p', '3p/2/5/20p']
            #   5-6/7-8p,15/1-2 => ['5/7p/1', '5/7p/2', '5/8p/1', '5/8p/2', '5/15/1', '5/15/2', '6/7p/1', '6/7p/2', '6/8p/1', '6/8p/2', '6/15/1', '6/15/2']

            components = subkey_paths.split("/")
            iterators = [range_iterator(c) for c in components]
            for v in itertools.product(*iterators):
                yield '/'.join(v)

        for subkey in subkey_iterator(path):
            yield self.subkey_for_path(subkey)

    def children(self, max_level=50, start_index=0, include_prime=True):
        for i in range(start_index, max_level + start_index + 1):
            yield self.subkey(i)
            if include_prime:
                yield self.subkey(i, is_prime=True)

    def __repr__(self):
        if self.child_number == 0:
            r = self.wallet_key(as_private=False)
        else:
            r = self.bitcoin_address()
        if self.is_private:
            return "private_for <%s>" % r
        return "<%s>" % r
