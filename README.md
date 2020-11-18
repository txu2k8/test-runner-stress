# stress-runner
A runner similar as TextTestRunner for stress test, support for html report.
Based on unittest, support iterative exection, html report, send html report, etc.

# Install
```shell script
pip install stressrunner -U
```

# Quick Start:
A TestRunner for use with the Python unit testing framework. It
generates a HTML report to show the result at a glance.
The simplest way to use this is to invoke its main method. E.g.
```python
from stressrunner import runner
# define your tests

if __name__ == '__main__':
    runner.main()
```
For more customization options, instantiates a StressRunner object.
StressRunner is a counterpart to unittest's TextTestRunner. E.g.
```python
# output to a file
from stressrunner import StressRunner

runner = StressRunner(
    report_path='./report/test.html',
    test_title='My unit test',
    desc='This demonstrates the report output by StressRunner.'
)
```
