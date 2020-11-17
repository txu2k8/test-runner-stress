# stress-runner
A runner similar as TextTestRunner for stress test, support for html report.
Based on unittest, support iterative exection, html report, send html report, etc.

# Quick Start:
A TestRunner for use with the Python unit testing framework. It
generates a HTML report to show the result at a glance.
The simplest way to use this is to invoke its main method. E.g.
```python
import unittest
from stressrunner import StressRunner
# define your tests

if __name__ == '__main__':
    StressRunner.main()
```
For more customization options, instantiates a StressRunner object.
StressRunner is a counterpart to unittest's TextTestRunner. E.g.
```python
# output to a file
from stressrunner import StressRunner

runner = StressRunner(
    report_path='./report/test.html',
    test_title='My unit test',
    desc='This demonstrates the report output by StressRunner.')
```
