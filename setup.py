#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
@file  : setup.py.py
@Time  : 2020/11/17 8:54
@Author: Tao.Xu
@Email : tao.xu2008@outlook.com
"""

import os
import sys
import re
from setuptools import setup


# 读取文件内容
def read_file(filename):
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(cur_dir, filename), encoding='utf-8') as f:
        long_desc = f.read()
    return long_desc


# 获取依赖
def read_requirements(filename):
    return [line.strip() for line in read_file(filename).splitlines()
            if not line.startswith('#')]


def _find_packages():
    """find pckages"""
    packages = []
    path = '.'
    for root, _, files in os.walk(path):
        if '__init__.py' in files:
            if sys.platform.startswith('linux'):
                item = re.sub('^[^A-z0-9_]', '', root.replace('/', '.'))
            elif sys.platform.startswith('win'):
                item = re.sub('^[^A-z0-9_]', '', root.replace('\\', '.'))
            else:
                item = re.sub('^[^A-z0-9_]', '', root.replace('/', '.'))
            if item is not None:
                packages.append(item.lstrip('.'))
    return packages


setup(
    name='stressrunner',
    python_requires='>=3.4.0',
    version='1.1.1',
    description="A stressrunner similar as TextTestRunner for stress test, support for html report.",
    long_description=read_file('README.md'),
    long_description_content_type="text/markdown",
    author="tao.xu",
    author_email='tao.xu2008@outlook.com',
    url='https://github.com/txu2k8/stress-runner',
    packages=_find_packages(),
    install_requires=read_requirements('requirements.txt'),
    include_package_data=True,
    license="MIT",
    keywords=['stress', 'stressrunner', 'html', 'unittest'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
)
