from ..script import opcodes, tools

from ... import encoding

from ...key.validate import netcode_and_type_for_data
from ...networks import address_prefix_for_netcode
from ...serialize import b2h

from .ScriptType import ScriptType, SolvingError

# see BIP11 https://github.com/bitcoin/bips/blob/master/bip-0011.mediawiki


class ScriptMultisig(ScriptType):

    def __init__(self, n, sec_keys):
        self.n = n
        self.sec_keys = sec_keys
        self._script = None

    @classmethod
    def from_script(cls, script):
        #TEMPLATE = m {pubkey}...{pubkey} n OP_CHECKMULTISIG
        pc = 0
        opcode, data, pc = tools.get_opcode(script, pc)

        if not opcodes.OP_1 <= opcode < opcodes.OP_16:
            raise ValueError("n value invalid")
        n = opcode + (1 - opcodes.OP_1)
        sec_keys = []
        while 1:
            opcode, data, pc = tools.get_opcode(script, pc)
            l = len(data)
            if l < 33 or l > 120:
                break
            sec_keys.append(data)
        m = opcode + (1 - opcodes.OP_1)
        if n > m or len(sec_keys) != m:
            raise ValueError("m value wrong")

        opcode, data, pc = tools.get_opcode(script, pc)
        if opcode != opcodes.OP_CHECKMULTISIG:
            raise ValueError("no OP_CHECKMULTISIG")
        if pc != len(script):
            raise ValueError("extra stuff at end")

        return cls(sec_keys=sec_keys, n=n)

    def address(self):
        if self._address is None:
            self._address = encoding.hash160_sec_to_bitcoin_address(
                self.hash160, address_prefix=self.address_prefix)
        return self._address

    def script(self):
        if self._script is None:
            # create the script
            #TEMPLATE = m {pubkey}...{pubkey} n OP_CHECKMULTISIG
            public_keys = [b2h(sk) for sk in self.sec_keys]
            script_source = "%d %s %d OP_CHECKMULTISIG" % (
                self.n, " ".join(public_keys), len(public_keys))
            self._script = tools.compile(script_source)
        return self._script

    def solve(self, **kwargs):
        """
        The kwargs required depend upon the script type.
        hash160_lookup:
            dict-like structure that returns a secret exponent for a hash160
        existing_script:
            existing solution to improve upon (optional)
        sign_value:
            the integer value to sign (derived from the transaction hash)
        signature_type:
            usually SIGHASH_ALL (1)
        """
        # we need a hash160 => secret_exponent lookup
        db = kwargs.get("hash160_lookup")
        if db is None:
            raise SolvingError("missing hash160_lookup parameter")

        sign_value = kwargs.get("sign_value")
        signature_type = kwargs.get("signature_type")

        existing_signatures = []
        existing_script = kwargs.get("existing_script")
        if existing_script:
            pc = 0
            opcode, data, pc = tools.get_opcode(script, pc)
            # ignore the first opcode
            while pc < len(data):
                opcode, data, pc = tools.get_opcode(script, pc)
                for sec_key in self.sec_keys:
                    sig_ok = check_signature(sign_value, sec_key, data,
                                             signature_type)
                    if sig_ok:
                        break
                else:
                    existing_signatures.append(data)

        for sec_key in self.sec_keys:
            if len(existing_signatures) >= self.n:
                break
            hash160 = encoding.hash160(sec_key)
            result = db.get(hash160)
            if result is None:
                continue
            secret_exponent, public_pair, compressed = result
            binary_signature = self._create_script_signature(
                secret_exponent, sign_value, signature_type)
            existing_signatures.append(binary_signature)
        DUMMY_SIGNATURE = self._dummy_signature(signature_type)
        while len(existing_signatures) < self.n:
            existing_signatures.append(DUMMY_SIGNATURE)

        script = "OP_0 %s" % " ".join(b2h(s) for s in existing_signatures)
        solution = tools.compile(script)
        return solution

    def info(self, netcode='BTC'):
        address_prefix = address_prefix_for_netcode(netcode)
        hash160s = [encoding.hash160(sk) for sk in self.sec_keys]
        addresses = [encoding.hash160_sec_to_bitcoin_address(
            h1, address_prefix=address_prefix) for h1 in hash160s]
        return dict(type="multisig m of n",
                    m=len(self.sec_keys),
                    n=self.n,
                    addresses=addresses,
                    hash160s=hash160s,
                    script=self._script,
                    address_prefix=address_prefix,
                    summary="%d of %s" % (self.n, addresses))

    def __repr__(self):
        info = self.info()
        return "<Script: multisig %d of %d (%s)>" % (
            info["n"], info["m"], "/".join(info["addresses"]))
