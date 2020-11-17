#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
@file  : test.py
@Time  : 2020/11/17 10:33
@Author: Tao.Xu
@Email : tao.xu2008@outlook.com
"""

import unittest
from stressrunner import StressRunner


class UnitTestCase(unittest.TestCase):

    def test_1(self):
        self.assertTrue('1')
        print("test 1")


if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(UnitTestCase)
    runner = StressRunner()
    runner.run(suite)
