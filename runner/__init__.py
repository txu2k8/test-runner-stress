#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
@file  : __init__.py.py
@Time  : 2020/11/17 10:15
@Author: Tao.Xu
@Email : tao.xu2008@outlook.com
"""

from .runner import *
__all__ = ['StressRunner']

"""
StressRunner - A runner similar as TextTestRunner for stress test, support for html report.
FYI: http://tungwaiyip.info/software/HTMLTestRunner.html
===============
Based on unittest.
Support iterative exection, html report, send html report, etc.
"""

if __name__ == '__main__':
    pass
