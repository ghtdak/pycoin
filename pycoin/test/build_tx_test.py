#!/usr/bin/env python

import io
import unittest

from pycoin.block import Block
from pycoin.serialize import h2b

from pycoin import ecdsa
from pycoin.encoding import public_pair_to_sec, public_pair_to_bitcoin_address, wif_to_secret_exponent

from pycoin.tx import Tx

# block 80971
block_80971_cs = h2b(
    '00000000001126456C67A1F5F0FF0268F53B4F22E0531DC70C7B69746AF69DAC')
block_80971_data = h2b('01000000950A1631FB9FAC411DFB173487B9E18018B7C6F7147E78C06258410000000000A881352F97F14B'\
'F191B54915AE124E051B8FE6C3922C5082B34EAD503000FC34D891974CED66471B4016850A040100'\
'0000010000000000000000000000000000000000000000000000000000000000000000FFFFFFFF080'\
'4ED66471B02C301FFFFFFFF0100F2052A01000000434104CB6B6B4EADC96C7D08B21B29D0ADA5F29F937'\
'8978CABDB602B8B65DA08C8A93CAAB46F5ABD59889BAC704925942DD77A2116D10E0274CAD944C71D3D1A'\
'670570AC0000000001000000018C55ED829F16A4E43902940D3D33005264606D5F7D555B5F67EE4C033390'\
'C2EB010000008A47304402202D1BF606648EDCDB124C1254930852D99188E1231715031CBEAEA80CCFD2B39A'\
'02201FA9D6EE7A1763580E342474FC1AEF59B0468F98479953437F525063E25675DE014104A01F763CFBF5E518'\
'C628939158AF3DC0CAAC35C4BA7BC1CE8B7E634E8CDC44E15F0296B250282BD649BAA8398D199F2424FCDCD88'\
'D3A9ED186E4FD3CB9BF57CFFFFFFFFF02404B4C00000000001976A9148156FF75BEF24B35ACCE3C05289A241'\
'1E1B0E57988AC00AA38DF010000001976A914BC7E692A5FFE95A596712F5ED83393B3002E452E88AC000000'\
'0001000000019C97AFDF6C9A31FFA86D71EA79A079001E2B59EE408FD418498219400639AC0A010000008B4'\
'830450220363CFFAE09599397B21E6D8A8073FB1DFBE06B6ACDD0F2F7D3FEA86CA9C3F605022100FA255A6ED'\
'23FD825C759EF1A885A31CAD0989606CA8A3A16657D50FE3CEF5828014104FF444BAC08308B9EC97F56A652A'\
'D8866E0BA804DA97868909999566CB377F4A2C8F1000E83B496868F3A282E1A34DF78565B65C15C3FA21A076'\
'3FD81A3DFBBB6FFFFFFFF02C05EECDE010000001976A914588554E6CC64E7343D77117DA7E01357A6111B798'\
'8AC404B4C00000000001976A914CA6EB218592F289999F13916EE32829AD587DBC588AC00000000010000000'\
'1BEF5C9225CB9FE3DEF929423FA36AAD9980B9D6F8F3070001ACF3A5FB389A69F000000004A493046022100F'\
'B23B1E2F2FB8B96E04D220D385346290A9349F89BBBC5C225D5A56D931F8A8E022100F298EB28294B90C1BAF'\
'319DAB713E7CA721AAADD8FCC15F849DE7B0A6CF5412101FFFFFFFF0100F2052A010000001976A9146DDEA80'\
'71439951115469D0D2E2B80ECBCDD48DB88AC00000000')

block_80971 = Block.parse(io.BytesIO(block_80971_data))

COINBASE_PUB_KEY_FROM_80971 = h2b("04cb6b6b4eadc96c7d08b21b29d0ada5f29f9378978cabdb602b8b65da08c8a93caab46"\
    "f5abd59889bac704925942dd77a2116d10e0274cad944c71d3d1a670570")
COINBASE_BYTES_FROM_80971 = h2b("04ed66471b02c301")


class BuildTxTest(unittest.TestCase):

    def test_standard_tx_out(self):
        coin_value = 10
        recipient_bc_address = '1BcJRKjiwYQ3f37FQSpTYM7AfnXurMjezu'
        tx_out = Tx.standard_tx([],
                                [(coin_value, recipient_bc_address)]).txs_out[0]
        s = str(tx_out)
        self.assertEqual(
            'TxOut<1E-7 "OP_DUP OP_HASH160 745e5b81fd30ca1e90311b012badabaa4411ae1a OP_EQUALVERIFY OP_CHECKSIG">',
            s)

    def test_coinbase_tx(self):
        coinbase_bytes = h2b("04ed66471b02c301")
        tx = Tx.coinbase_tx(COINBASE_PUB_KEY_FROM_80971, int(50 * 1e8),
                            COINBASE_BYTES_FROM_80971)
        s = io.BytesIO()
        tx.stream(s)
        tx1 = s.getvalue()
        s = io.BytesIO()
        block_80971.txs[0].stream(s)
        tx2 = s.getvalue()
        self.assertEqual(tx1, tx2)

    def test_build_spends(self):
        # create a coinbase Tx where we know the public & private key

        exponent = wif_to_secret_exponent(
            "5JMys7YfK72cRVTrbwkq5paxU7vgkMypB55KyXEtN5uSnjV7K8Y")
        compressed = False

        public_key_sec = public_pair_to_sec(
            ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1,
                                                  exponent),
            compressed=compressed)

        the_coinbase_tx = Tx.coinbase_tx(public_key_sec, int(50 * 1e8),
                                         COINBASE_BYTES_FROM_80971)

        # now create a Tx that spends the coinbase

        compressed = False

        exponent_2 = int(
            "137f3276686959c82b454eea6eefc9ab1b9e45bd4636fb9320262e114e321da1",
            16)
        bitcoin_address_2 = public_pair_to_bitcoin_address(
            ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1,
                                                  exponent_2),
            compressed=compressed)

        self.assertEqual("12WivmEn8AUth6x6U8HuJuXHaJzDw3gHNZ",
                         bitcoin_address_2)

        TX_DB = dict((tx.hash(), tx) for tx in [the_coinbase_tx])

        coins_from = [(the_coinbase_tx.hash(), 0)]
        coins_to = [(int(50 * 1e8), bitcoin_address_2)]
        coinbase_spend_tx = Tx.standard_tx(coins_from, coins_to, TX_DB,
                                           [exponent])
        coinbase_spend_tx.validate(TX_DB)

        ## now try to respend from priv_key_2 to priv_key_3

        compressed = True

        exponent_3 = int(
            "f8d39b8ecd0e1b6fee5a340519f239097569d7a403a50bb14fb2f04eff8db0ff",
            16)
        bitcoin_address_3 = public_pair_to_bitcoin_address(
            ecdsa.public_pair_for_secret_exponent(ecdsa.generator_secp256k1,
                                                  exponent_3),
            compressed=compressed)

        self.assertEqual("13zzEHPCH2WUZJzANymow3ZrxcZ8iFBrY5",
                         bitcoin_address_3)

        TX_DB = dict((tx.hash(), tx) for tx in [coinbase_spend_tx])

        spend_tx = Tx.standard_tx([(coinbase_spend_tx.hash(), 0)],
                                  [(int(50 * 1e8), bitcoin_address_3)], TX_DB,
                                  [exponent_2])

        spend_tx.validate(TX_DB)


if __name__ == '__main__':
    unittest.main()
