#!/bin/bash
# ##########################################################################
# Author: txu
# Brief:  Upload tlib to pypi
#
# Returns:
#   pass: 0
#   fail: not 0
# ##########################################################################

# pip install wheel
# pip install twine

rm -rf ./build ./storage_test.egg-info ./dist
python setup.py sdist bdist_wheel
twine upload  dist/*