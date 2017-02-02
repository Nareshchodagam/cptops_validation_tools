import unittest
import check_mounts_siteaware
import socket

class TestRegex(unittest.TestCase):

    def test_check_prod(self):
        self.insts = []
        for pod in ['cs', 'na', 'eu']:
            for i in range(30):
                inst = pod + str(i)
                self.insts.append(inst)


        self.locs = {}
        for h in self.insts:
            self.locs[h] = check_mounts_siteaware.check_prod(h, 'was')
        self.assertTrue(self.locs['na7'] == 'PROD', 'Should have returned prod')
        self.assertTrue(self.locs['na4'] == 'PROD', 'Should have returned prod')
        self.assertTrue(self.locs['eu0'] == 'PROD', 'Should have returned prod')
        self.assertTrue(self.locs['cs19'] == 'DR', 'Should have returned DR')
        self.assertTrue(self.locs['cs16'] == 'DR', 'Should have returned DR')
        self.assertTrue(self.locs['eu5'] == 'DR', 'Should have returned DR')
        self.assertTrue(self.locs['cs0'] == 'UNKNOWN', 'Should have returned UNKNOWN')
        for h in self.insts:
            self.locs[h] = check_mounts_siteaware.check_prod(h, 'chi')
        self.assertTrue(self.locs['na7'] == 'DR', 'Should have returned DR')
        self.assertTrue(self.locs['cs18'] != 'PROD', 'Should have returned DR')
        self.assertTrue(self.locs['na4'] == 'DR', 'Should have returned DR')
        self.assertTrue(self.locs['eu0'] == 'DR', 'Should have returned DR')
        self.assertTrue(self.locs['cs24'] == 'PROD', 'Should have returned prod')
        self.assertTrue(self.locs['na20'] == 'PROD', 'Should have returned prod')
        self.assertTrue(self.locs['eu1'] == 'PROD', 'Should have returned prod')
if __name__ == '__main__':
    unittest.main()
