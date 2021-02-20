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
        print("---- test1 test1 test1 test1 test1 ...")

    def atest_2(self):
        import random
        self.assertEqual(1, random.choice(range(3)))
        print("---- test2 test2 test2 test2 test2 ...")

    def test_3(self):
        self.assertTrue('1')
        print("---- test3 test3 test3 test3 test3 ...")


def teardown():
    print("teardown teardown teardown ...")


if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(UnitTestCase)
    runner = StressRunner(iteration=3,
                          description='stress unittest', test_version='1.2.3',
                          report_title='report-1.2.3', test_env={'sss': 123})
    runner.run(suite)
    teardown()
    # runner.send_mail()
