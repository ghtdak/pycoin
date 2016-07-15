#!/usr/bin/env python

import io
import unittest

from pycoin.block import Block
from pycoin.serialize import b2h_rev, h2b


class BlockTest(unittest.TestCase):
    def test_block(self):
        expected_checksum = '0000000000089F7910F6755C10EA2795EC368A29B435D80770AD78493A6FECF1'.lower(
        )

        block_data = h2b(
            '010000007480150B299A16BBCE5CCDB1D1BBC65CFC5893B01E6619107C55200000000000790' \
            '0A2B203D24C69710AB6A94BEB937E1B1ADD64C2327E268D8C3E5F8B41DBED8796974CED66471B204C3247030' \
            '1000000010000000000000000000000000000000000000000000000000000000000000000FFFFFFFF0804ED6' \
            '6471B024001FFFFFFFF0100F2052A010000004341045FEE68BAB9915C4EDCA4C680420ED28BBC369ED84D48A' \
            'C178E1F5F7EEAC455BBE270DABA06802145854B5E29F0A7F816E2DF906E0FE4F6D5B4C9B92940E4F0EDAC000' \
            '000000100000001F7B30415D1A7BF6DB91CB2A272767C6799D721A4178AA328E0D77C199CB3B57F010000008' \
            'A4730440220556F61B84F16E637836D2E74B8CB784DE40C28FE3EF93CCB7406504EE9C7CAA5022043BD4749D' \
            '4F3F7F831AC696748AD8D8E79AEB4A1C539E742AA3256910FC88E170141049A414D94345712893A828DE57B4C' \
            '2054E2F596CDCA9D0B4451BA1CA5F8847830B9BE6E196450E6ABB21C540EA31BE310271AA00A49ED0BA930743' \
            'D1ED465BAD0FFFFFFFF0200E1F505000000001976A914529A63393D63E980ACE6FA885C5A89E4F27AA08988AC' \
            'C0ADA41A000000001976A9145D17976537F308865ED533CCCFDD76558CA3C8F088AC000000000100000001651' \
            '48D894D3922EF5FFDA962BE26016635C933D470C8B0AB7618E869E3F70E3C000000008B48304502207F5779EB' \
            'F4834FEAEFF4D250898324EB5C0833B16D7AF4C1CB0F66F50FCF6E85022100B78A65377FD018281E77285EFC3' \
            '1E5B9BA7CB7E20E015CF6B7FA3E4A466DD195014104072AD79E0AA38C05FA33DD185F84C17F611E58A8658CE' \
            '996D8B04395B99C7BE36529CAB7606900A0CD5A7AEBC6B233EA8E0FE60943054C63620E05E5B85F0426FFFFF' \
            'FFF02404B4C00000000001976A914D4CAA8447532CA8EE4C80A1AE1D230A01E22BFDB88AC8013A0DE0100000' \
            '01976A9149661A79AE1F6D487AF3420C13E649D6DF3747FC288AC00000000')

        # try to parse a block

        block = Block.parse(io.BytesIO(block_data))

        print(block)
        assert b2h_rev(block.hash()) == expected_checksum

        for tx in block.txs:
            print(tx)
            for t in tx.txs_in:
                print("  %s" % t)
            for t in tx.txs_out:
                print("  %s" % t)

        block.check_merkle_hash()


def main():
    unittest.main()


if __name__ == "__main__":
    main()
