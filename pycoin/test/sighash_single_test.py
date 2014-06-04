#!/usr/bin/env python

import unittest
from pycoin.encoding import to_bytes_32
from pycoin.key import Key
from pycoin.serialize import (b2h,
                              b2h_rev,)
from pycoin.tx import (Tx,
                       TxIn,
                       TxOut,)
from pycoin.tx.Tx import (SIGHASH_ANYONECANPAY,
                          SIGHASH_SINGLE,)
from pycoin.tx.TxOut import standard_tx_out_script
from pycoin.tx.script.tools import compile as pycoin_compile

PRIV_KEYS = (
    2330949616242593315303241053456316633827293588958882755297900732239663851861L,
    4437411780076344925846479906614060621668407514498402815534040340772719979673L,
    14311886404724799688521454580288220586308410691395501373612453626821267193196L,
    16404731722033649474165521611800542240555275746052963990137782680023514762282L,
    92715304942310420502826004911529506622922082818576946681102234225452853924813L,
    103235678552410630318322729483874198805317322052500844759252733409163632402845L,
)


#=========================================================================
class SighashSingleTest(unittest.TestCase):

    #=====================================================================
    def test_sighash_single_mainnet(self):
        self._test_sighash_single('BTC')

    #=====================================================================
    def test_sighash_single_testnet3(self):
        self._test_sighash_single('XTN')

    #=====================================================================
    def _test_sighash_single(self, netcode):
        k0 = Key(secret_exponent=PRIV_KEYS[0],
                 is_compressed=True,
                 netcode=netcode)
        k1 = Key(secret_exponent=PRIV_KEYS[1],
                 is_compressed=True,
                 netcode=netcode)
        k2 = Key(secret_exponent=PRIV_KEYS[2],
                 is_compressed=True,
                 netcode=netcode)
        k3 = Key(secret_exponent=PRIV_KEYS[3],
                 is_compressed=True,
                 netcode=netcode)
        k4 = Key(secret_exponent=PRIV_KEYS[4],
                 is_compressed=True,
                 netcode=netcode)
        k5 = Key(secret_exponent=PRIV_KEYS[5],
                 is_compressed=True,
                 netcode=netcode)

        # Fake a coinbase transaction
        coinbase_tx = Tx.coinbase_tx(k0.sec(), 500000000)
        coinbase_tx.txs_out.append(TxOut(1000000000, pycoin_compile(
            '%s OP_CHECKSIG' % b2h(k1.sec()))))
        coinbase_tx.txs_out.append(TxOut(1000000000, pycoin_compile(
            '%s OP_CHECKSIG' % b2h(k2.sec()))))

        self.assertEqual(
            '2acbe1006f7168bad538b477f7844e53de3a31ffddfcfc4c6625276dd714155a',
            b2h_rev(coinbase_tx.hash()))

        # Make the test transaction
        txs_in = [
            TxIn(coinbase_tx.hash(), 0),
            TxIn(coinbase_tx.hash(), 1),
            TxIn(coinbase_tx.hash(), 2),
        ]
        txs_out = [
            TxOut(900000000, standard_tx_out_script(k3.address())),
            TxOut(800000000, standard_tx_out_script(k4.address())),
            TxOut(800000000, standard_tx_out_script(k5.address())),
        ]
        tx = Tx(1, txs_in, txs_out)

        self.assertEqual(
            '791b98ef0a3ac87584fe273bc65abd89821569fd7c83538ac0625a8ca85ba587',
            b2h_rev(tx.hash()))
        self.assertEqual(
            'cc52d785a3b4133504d1af9e60cd71ca422609cb41df3a08bbb466b2a98a885e',
            b2h(to_bytes_32(tx.signature_hash(coinbase_tx.txs_out[0].script, 0,
                                              SIGHASH_SINGLE))))
        self.assertEqual(
            '2003393d246a7f136692ce7ab819c6eadc54ffea38eb4377ac75d7d461144e75',
            b2h(to_bytes_32(tx.signature_hash(coinbase_tx.txs_out[
                0].script, 0, SIGHASH_SINGLE | SIGHASH_ANYONECANPAY))))
        self.assertEqual(
            '93bb883d70fccfba9b8aa2028567aca8357937c65af7f6f5ccc6993fd7735fb7',
            b2h(to_bytes_32(tx.signature_hash(coinbase_tx.txs_out[1].script, 1,
                                              SIGHASH_SINGLE))))
        self.assertEqual(
            'e3f469ac88e9f35e8eff0bd8ad4ad3bf899c80eb7645947d60860de4a08a35df',
            b2h(to_bytes_32(tx.signature_hash(coinbase_tx.txs_out[
                1].script, 1, SIGHASH_SINGLE | SIGHASH_ANYONECANPAY))))
        self.assertEqual(
            '53ef7f67c3541bffcf4e0d06c003c6014e2aa1fb38ff33240b3e1c1f3f8e2a35',
            b2h(to_bytes_32(tx.signature_hash(coinbase_tx.txs_out[2].script, 2,
                                              SIGHASH_SINGLE))))
        self.assertEqual(
            'bacd7c3ab79cad71807312677c1788ad9565bf3c00ab9a153d206494fb8b7e6a',
            b2h(to_bytes_32(tx.signature_hash(coinbase_tx.txs_out[
                2].script, 2, SIGHASH_SINGLE | SIGHASH_ANYONECANPAY))))


if __name__ == "__main__":
    unittest.main()
