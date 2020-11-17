# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/8/26 16:56
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

#  ____  _                       ____
# / ___|| |_ _ __ ___  ___ ___  |  _ \ _   _ _ __  _ __   ___ _ __
# \___ \| __| '__/ _ \/ __/ __| | |_) | | | | '_ \| '_ \ / _ \ '__|
#  ___) | |_| | |  __/\__ \__ \ |  _ <| |_| | | | | | | |  __/ |
# |____/ \__|_|  \___||___/___/ |_| \_\\__,_|_| |_|_| |_|\___|_|

"""StressRunner
Require: python3+

Description and Quick Start:
A TestRunner for use with the Python unit testing framework. It
generates a HTML report to show the result at a glance.
The simplest way to use this is to invoke its main method. E.g.
    import unittest
    import StressRunner
    ... define your tests ...
    if __name__ == '__main__':
        StressRunner.main()
For more customization options, instantiates a StressRunner object.
StressRunner is a counterpart to unittest's TextTestRunner. E.g.
    # output to a file
    stressrunner = StressRunner.StressRunner(
                report_path='./report/',
                test_title='My unit test',
                desc='This demonstrates the report output by StressRunner.'
                )
"""

import logging
import coloredlogs
import copy
import re
import os
import sys
from datetime import date, datetime
import io
import socket
import traceback
from xml.sax import saxutils
import unittest

from stressrunner.mail import send_mail
from stressrunner.report import REPORT_TEMPLATE

# =============================
# --- Global
# =============================
__author__ = "tao.xu"
__version__ = "1.5.1"
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
PY2 = sys.version_info[0] == 2
sys.setrecursionlimit(100000)
# Python2 basestring,  --> (str, unicode)
string_types = basestring if PY2 else str, bytes

DEFAULT_LOGGER_FORMATE = '%(asctime)s %(name)s %(levelname)s: %(message)s'
DEFAULT_LOGGER = logging.getLogger('StressRunner')
coloredlogs.install(logger=DEFAULT_LOGGER, level=logging.DEBUG,
                    fmt=DEFAULT_LOGGER_FORMATE)

# default report_path
CUR_DIR = os.getcwd()
DEFAULT_REPORT_PATH = os.path.join(CUR_DIR, 'report.html')
DEFAULT_TITLE = 'Test Report'
DEFAULT_DESCRIPTION = ''
DEFAULT_TESTER = __author__
STATUS = {
    0: 'PASS',
    1: 'FAIL',
    2: 'ERROR',
    3: 'SKIP',
    4: 'PASS(Canceled By User)',
}


class MailInfo(object):
    """Define the mail info attributes here"""

    def __init__(self, m_from="", m_to="", host="", user="", password="", port=465, tls=True,
                 subject="Test Report", content="", attachments=None):
        self.m_from = m_from
        self.m_to = m_to
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.tls = tls
        self.subject = subject
        self.content = content
        self.attachments = attachments or []


def get_local_ip():
    """
    Get the local ip address --linux/windows
    :return:(char) local_ip
    """
    return socket.gethostbyname(socket.gethostname())


def get_local_hostname():
    """
    Get the local ip address --linux/windows
    :return:
    """
    return socket.gethostname()


def escape(value):
    """
    Escape a single value of a URL string or a query parameter. If it is a list
    or tuple, turn it into a comma-separated string first.
    :param value:
    :return: escape value
    """

    # make sequences into comma-separated stings
    if isinstance(value, (list, tuple)):
        value = ",".join(value)

    # dates and datetimes into isoformat
    elif isinstance(value, (date, datetime)):
        value = value.isoformat()

    # make bools into true/false strings
    elif isinstance(value, bool):
        value = str(value).lower()

    # don't decode bytestrings
    elif isinstance(value, bytes):
        return value

    # encode strings to utf-8
    if isinstance(value, string_types):
        if PY2 and isinstance(value, unicode):
            return value.encode("utf-8")
        if not PY2 and isinstance(value, str):
            return value.encode("utf-8")

    return str(value)


# ------------------------------------------------------------------------
# The redirectors below are used to capture output during testing. Output
# sent to sys.stdout and sys.stderr are automatically captured. However
# in some cases sys.stdout is already cached before StressRunner is
# invoked (e.g. calling logging.basicConfig). In order to capture those
# output, use the redirectors for the cached stream.
#
# e.g.
#   >>> logging.basicConfig(stream=StressRunner.stdout_redirector)
#   >>>


class OutputRedirector(object):
    """ Wrapper to redirect stdout or stderr """

    def __init__(self, fp):
        self.fp = fp
        self.__console__ = sys.stdout

    def write(self, s):
        if 'ERROR:' in s:
            if WINDOWS:
                pattern = re.compile(r'[^a]\W\d+[m]')
            elif POSIX:
                pattern = re.compile(r'[^a]\W\d+[m]\W?')
            else:
                pattern = re.compile(r'')
            s_mesg = pattern.sub('', s + "\n")
            s_mesg = s_mesg.encode(encoding="utf-8")
            self.fp.write(s_mesg)

        if 'DESCRIBE:' in s:
            pattern = re.compile(r'.+DESCRIBE:\W+\d+[m]\s')
            s_mesg = pattern.sub('', s + "\n")
            s_mesg = s_mesg.encode(encoding="utf-8")
            self.fp.write(s_mesg)
        self.__console__.write(str(s))

    def writelines(self, lines):
        if 'ERROR' in lines:
            self.fp.writelines(lines)
        self.__console__.write(str(lines))

    def flush(self):
        self.fp.flush()
        self.__console__.flush()


stdout_redirector = OutputRedirector(sys.stdout)
stderr_redirector = OutputRedirector(sys.stderr)
STDOUT_LINE = '\nStdout:\n%s'
STDERR_LINE = '\nStderr:\n%s'


class _TestResult(unittest.TestResult):
    """
    note: _TestResult is a pure representation of results.
    It lacks the output and reporting ability compares to
    unittest._TextTestResult.
    """

    p_msg = "[ PASS ] {0} -- iteration: {1} --Elapsed Time: {2}"
    e_msg = "[ERROR ] {0} -- iteration: {1} --Elapsed Time: {2}"
    f_msg = "[FAILED] {0} -- iteration: {1} --Elapsed Time: {2}"
    s_msg = "[ SKIP ] {0} -- iteration: {1} --Elapsed Time: {2}"

    def __init__(self, logger=DEFAULT_LOGGER, verbosity=2, tc_loop_limit=1,
                 tc_elapsed_limit=None, save_last_result=False):
        """
        _TestResult inherit from unittest TestResult
        :param logger: default is logging.get_logger()
        :param verbosity: 1-dots, 2-showStatus, 3-showAll
        :param tc_loop_limit: the max loop running for each test case
        :param tc_elapsed_limit:None means no limit
        :param save_last_result: just save the last loop result
        """

        super(_TestResult, self).__init__()
        # TestResult.__init__(self)
        self.logger = logger
        self.verbosity = verbosity
        self.tc_loop_limit = tc_loop_limit
        self.tc_elapsed_limit = tc_elapsed_limit
        self.save_last_result = save_last_result

        self.showAll = verbosity >= 3
        self.showStatus = verbosity == 2
        self.dots = verbosity <= 1
        self.stdout0 = None
        self.stderr0 = None

        self._stdout_buffer = None
        self._stderr_buffer = None
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        self.skipped_count = 0  # add skipped_count
        self.canceled_count = 0  # add canceled_count

        '''
        result is a list of tuple
        (
          result code (0: success; 1: fail; 2: error),
          TestCase object,
          Test output (byte string),
          stack trace,
        )
        '''
        self.status = 0
        self.result = []
        self.outputBuffer = ''

        self.tc_loop = 0
        self.ts_loop = 1
        self.tc_start_time = datetime.now()
        self.ts_start_time = datetime.now()  # test suite start time

    @staticmethod
    def _get_description(test):
        return test.shortDescription() or str(test)

    def _setup_output(self):
        if self._stderr_buffer is None:
            self._stderr_buffer = io.BytesIO()
            self._stdout_buffer = io.BytesIO()
            self._stdout_buffer.seek(0)
            self._stdout_buffer.truncate()
            self._stderr_buffer.seek(0)
            self._stderr_buffer.truncate()
        stdout_redirector.fp = self._stdout_buffer
        stderr_redirector.fp = self._stderr_buffer
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector

    def _restore_output(self, test):
        """
        Disconnect output redirection and return buffer.
        Safe to call multiple times.
        """
        # remove the running record
        if len(self.result) > 0:
            self.result.pop(-1)

        output = sys.stdout.fp.getvalue().decode('UTF-8')
        error = sys.stderr.fp.getvalue().decode('UTF-8')
        output_info = ''
        if output:
            if not output.endswith('\n'):
                output += '\n'
            output_info += output
            # self._original_stdout.write(STDOUT_LINE % output)
        if error:
            if not error.endswith('\n'):
                error += '\n'
            output_info += error
            # self._original_stderr.write(STDERR_LINE % error)
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._stdout_buffer.seek(0)
        self._stdout_buffer.truncate()
        self._stderr_buffer.seek(0)
        self._stderr_buffer.truncate()

        tc_stop_time = datetime.now()
        tc_elapsedtime = str(tc_stop_time - self.tc_start_time).split('.')[0]
        ts_elapsedtime = str(tc_stop_time - self.ts_start_time).split('.')[0]
        for test_item, err in (self.errors + self.failures):
            if test_item == test:
                output_info += "{test_info}:".format(test_info=test)

        return output_info, tc_elapsedtime, ts_elapsedtime

    def startTest(self, test):
        self.logger.info("[START ] {0} -- iteration: {1}".format(
            str(test), self.ts_loop))
        self.result.append((4, test, '', '', '', self.ts_loop))
        self.tc_start_time = datetime.now()
        unittest.TestResult.startTest(self, test)
        self._setup_output()

    def stopTest(self, test):
        """
        Called when the given test has been run

        Usually one of addSuccess, addError or addFailure would have been
        called. But there are some path in unittest that would bypass this.
        We must disconnect stdout in stopTest(), which is guaranteed to be
        called.
        :param test:
        :return:
        """
        pass
        # unittest.TestResult.stopTest(self, test)
        # self.complete_output(test)

    def addSuccess(self, test):
        self.status = 0
        self.tc_loop += 1
        self.success_count += 1
        unittest.TestResult.addSuccess(self, test)

        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.result.append(
            (self.status, test, output, '', tc_elapsedtime, self.ts_loop)
        )
        if self.showAll:
            self.logger.info(
                self.p_msg.format(str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.info(STATUS[self.status])
        elif self.dots:
            self.logger.info("\n.")
        else:
            pass

        # calculate retry or not
        if (self.tc_loop_limit == 0) or (self.tc_loop_limit > self.tc_loop):
            retry_flag = True
        elif self.tc_elapsed_limit:
            retry_flag = True
            self.tc_elapsed_limit -= tc_elapsedtime
        else:
            retry_flag = False

        # recursive retry test
        if retry_flag:
            if self.save_last_result:
                self.result.pop(-1)
                self.success_count -= 1
            test = copy.copy(test)
            self.tc_start_time = datetime.now()
            test(self)
        else:
            self.tc_loop = 0  # update for next test case loop=0

    def addError(self, test, err):
        self.status = 2
        self.error_count += 1
        unittest.TestResult.addError(self, test, err)
        _, str_e = self.errors[-1]
        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.result.append(
            (self.status, test, output, str_e, tc_elapsedtime, self.ts_loop)
        )
        if self.showAll:
            self.logger.critical(
                self.e_msg.format(str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.critical(STATUS[self.status])
        else:
            self.logger.critical("\nE")
        self.tc_loop = 0
        # self.logger.info("Stop test while test meet ERROR ...")  TODO

    def addFailure(self, test, err):
        self.status = 1
        self.failure_count += 1
        unittest.TestResult.addFailure(self, test, err)
        _, str_e = self.failures[-1]
        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.result.append(
            (self.status, test, output, str_e, tc_elapsedtime, self.ts_loop)
        )
        if self.showAll:
            self.logger.critical(
                self.e_msg.format(str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.critical(STATUS[self.status])
        else:
            self.logger.critical("\nF")
        self.tc_loop = 0
        # self.logger.info("Stop test while test meet FAILED ...")  TODO

    def addSkip(self, test, reason):
        self.status = 3
        self.skipped_count += 1
        unittest.TestResult.addSkip(self, test, reason)
        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.result.append(
            (self.status, test, output, reason, tc_elapsedtime, self.ts_loop)
        )
        if self.showAll:
            self.logger.warning(
                self.e_msg.format(str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.warning(STATUS[self.status])
        else:
            self.logger.warning("\nS")
        self.tc_loop = 0

    def print_error_list(self, flavour, errors):
        for test, err in errors:
            self.logger.error("{0}: {1}\n{2}".format(
                flavour, self._get_description(test), err))

    def print_errors(self):
        if self.dots or self.showAll:
            sys.stderr.write('\n')
        self.print_error_list('ERROR', self.errors)
        self.print_error_list('FAIL', self.failures)


class StressRunner(object):
    """
    stress stressrunner
    """

    local_hostname = get_local_hostname()
    local_ip = get_local_ip()

    def __init__(self,
                 report_path=DEFAULT_REPORT_PATH,
                 logger=DEFAULT_LOGGER,
                 iteration=1,
                 verbosity=2,
                 tc_elapsed_limit=None,
                 save_last_result=False,
                 desc=DEFAULT_DESCRIPTION,
                 tester=DEFAULT_TESTER,
                 test_title=DEFAULT_TITLE,
                 test_version='',
                 test_env=None,
                 test_nodes=None,
                 mail_info=MailInfo(),
                 teardown_fn=None,
                 ):
        """
        Stress stressrunner
        Args:
            report_path: default ./report.html
            logger:
            iteration: the max test iteration
            verbosity:
            tc_elapsed_limit: the test case run time limit
            save_last_result: Save only the last iteration results if true
            desc:
            tester:
            test_title:
            test_version:
            test_env: test env k-v info
            test_nodes: test env nodes info
            mail_info: info for send emails
            teardown_fn: The Fn() run after test done
        """

        if test_env is None:
            test_env = []
        if not isinstance(test_env, list):
            test_env = [test_env]

        self.report_path = report_path if report_path.endswith('.html') else report_path + '.html'
        self.logger = logger
        self.iteration = iteration
        self.verbosity = verbosity
        self.tc_elapsed_limit = tc_elapsed_limit
        self.save_last_result = save_last_result

        self.desc = desc
        self.tester = tester
        self.title = test_title + '-' + test_version if test_version else test_title
        self.test_version = test_version
        self.test_env = test_env
        self.test_nodes = test_nodes
        self.mail_info = mail_info
        self.teardown_fn = teardown_fn

        # test status
        self.start_time = datetime.now()
        self.stop_time = ''
        self.elapsedtime = ''
        self.passrate = ''
        self.summary = ''  # eg: "ALL 1, PASS 1, Passing rate: 100%"

    def run(self, test):
        """
        Run the given test case or test suite
        :param test: unittest.testSuite
        :return:
        """
        tc_loop_limit = 1  # each case run only 1 loop in one iteration
        _result = _TestResult(self.logger, self.verbosity, tc_loop_limit,
                              self.tc_elapsed_limit, self.save_last_result)
        test_status = 'ERROR'
        retry_flag = True
        # result.ts_loop = 1
        try:
            while retry_flag:
                # retry test suite by iteration
                running_test = copy.deepcopy(test)
                self.logger.info("Test Case List:")
                for _test in running_test._tests:
                    self.logger.info(_test)

                running_test(_result)
                _result.ts_loop += 1
                fail_count = _result.failure_count + _result.error_count
                test_status = 'FAILED' if fail_count > 0 else 'PASSED'

                if fail_count > 0:
                    retry_flag = False
                elif self.iteration == 0 or self.iteration >= _result.ts_loop:
                    retry_flag = True
                else:
                    retry_flag = False

        except KeyboardInterrupt:
            self.logger.info("Script stoped by user --> ^C")
            if (_result.failure_count + _result.error_count) > 0:
                test_status = 'FAILED'
            elif _result.success_count <= 0:
                test_status = 'CANCELED'
            else:
                test_status = 'PASSED'
            _result.canceled_count += 1
            cancled_time = str(datetime.now() - _result.tc_start_time).split('.')[0]
            n, t, o, e, d, lp = _result.result[-1]
            if n == 4:
                _result.result.pop(-1)
                _result.result.append((n, t, o, e, cancled_time, lp))
        except Exception as e:
            self.logger.error(e)
            self.logger.error('{err}'.format(err=traceback.format_exc()))
            failed_time = str(datetime.now() - _result.tc_start_time).split('.')[0]
            n, t, o, e, d, lp = _result.result[-1]
            if n == 4:
                _result.result.pop(-1)
                _result.result.append((2, t, o, e, failed_time, lp))
        finally:
            self.logger.info(_result)
            if _result.testsRun < 1:
                return _result
            self.stop_time = datetime.now()
            self.elapsedtime = str(self.stop_time - self.start_time).split('.')[0]
            self.title = test_status + ": " + self.title
            self.generate_report(_result)

            # self.logger.info('=' * 50)
            # self.logger.info("Errors & Failures:")
            # _result.printErrors()

            self.logger.info('=' * 50)
            for res in _result.result:
                msg = "{stat} - {tc} - Iteration: {iter} - Elapsed: {elapsed}" \
                    .format(stat=STATUS[res[0]], tc=res[1], iter=res[5], elapsed=res[4])
                self.logger.info(msg)
                # res[2].strip('\n') + res[3].strip('\n')
                err_failure = res[3].strip('\n')
                if err_failure:
                    self.logger.error(err_failure)
            if not _result.result:
                for _test in test._tests:
                    self.logger.info(_test)

            total_count = sum([
                _result.success_count,
                _result.failure_count,
                _result.error_count,
                _result.skipped_count,
                _result.canceled_count])
            self.logger.info("Pass: {0}".format(_result.success_count))
            self.logger.info("Fail: {0}".format(_result.failure_count))
            self.logger.info("Error: {0}".format(_result.error_count))
            self.logger.info("Skipped: {0}".format(_result.skipped_count))
            self.logger.info("Canceled: {0}".format(_result.canceled_count))
            self.logger.info("Total: {0}".format(total_count))
            self.logger.info('Time Elapsed: {0}'.format(self.elapsedtime))
            self.logger.info('Report Path: {0}'.format(self.report_path))
            self.logger.info('Test Location: {0}({1})'.format(
                self.local_hostname, self.local_ip))
            self.logger.info('=' * 50)

            # send email
            if self.mail_info.m_to:
                self.mail_info.subject = self.title
                with open(self.report_path, 'rb') as f:
                    self.mail_info.content = f.read()
                log_path = self.report_path.replace('.html', '.log')
                if os.path.getsize(log_path) < 2048 * 1000:
                    self.mail_info.attachments.append(log_path)
                # self.mail_info.attachments.append(self.report_path)
                send_mail(self.mail_info)
                print(">> Send mail done.")

            # -- extend operations here -----------------------------------
            # eg: write test result to mysql
            # eg: tar and backup test logs
            if self.teardown_fn:
                self.teardown_fn()

            return _result, test_status

    @staticmethod
    def sort_result(result_list):
        """
        unittest does not seems to run in any particular order.
        Here at least we want to group them together by class.

        :param result_list:
        :return:
        """

        rmap = {}
        classes = []
        for n, t, o, e, d, l in result_list:
            cls = t.__class__
            if cls not in rmap:
                rmap[cls] = []
                classes.append(cls)
            rmap[cls].append((n, t, o, e, d, l))
        r = [(cls, rmap[cls]) for cls in classes]
        return r

    def _get_attributes(self, result):
        """
        Return report attributes as a list of (name, value).
        Override this to add custom attributes.
        :param result:
        :return:
        """

        status = []
        total_count = sum([
            result.success_count,
            result.failure_count,
            result.error_count,
            result.skipped_count,
            result.canceled_count]
        )
        pass_count = result.success_count + result.canceled_count
        exec_count = total_count - result.skipped_count

        status.append('ALL {0}'.format(total_count))
        if result.success_count:
            status.append('Pass {0}'.format(result.success_count))
        if result.failure_count:
            status.append('Failure {0}'.format(result.failure_count))
        if result.error_count:
            status.append('Error {0}'.format(result.error_count))
        if result.skipped_count:
            status.append('Skip {0}'.format(result.skipped_count))
        if result.canceled_count:
            status.append('Cancel {0}'.format(result.canceled_count))

        status = ', '.join(status)
        if exec_count > 0:
            self.passrate = str("%.0f%%" % (float(pass_count) / float(exec_count) * 100))
        else:
            self.passrate = str("%.0f%%" % (float(0)))
        self.summary = status + ", Passing rate: " + self.passrate

        attr = {
            'Tester': self.tester,
            'Version': self.test_version,
            'Start': str(self.start_time).split('.')[0],
            'End': str(self.stop_time).split('.')[0],
            'Elapsed': self.elapsedtime,
            'Summary': self.summary,
            'Location': '{0}({1})'.format(self.local_hostname, self.local_ip),
            'Report': self.report_path,
            'Command': 'python ' + ' '.join(sys.argv),
        }

        return attr

    def _get_attributes_table_string(self, result):
        """
        get attributes table_string
        """
        att_template = """
        <tr id='attr_%d' class='attr'>
            <td colspan='1' align='left' width='8%%'>%s</td>
            <td colspan='1' align='left'>%s</td>
        </tr>
        """
        tr = ""
        attr = self._get_attributes(result)
        for idx, (k, v) in enumerate(attr.items()):
            idx += 1
            if v:
                tr += att_template % (idx, k, v)
        return tr

    def _get_nodes_table_string(self, nodes_info=None):
        """
        nodes_info [
            {
                Name:''
                Status:''
                IPAddress:''
                Roles:''
                User:''
                Password:''
            }
        ]
        """
        if nodes_info is None:
            nodes_info = []
        nodes_info.insert(0, {
            "Name": self.local_hostname,
            "Status": "Ready",
            "IPAddress": self.local_ip,
            "Roles": "Test Host",
            "User": "root",
            "Password": "password",
        })
        html_template = """
        <tr id='node_%d' class='nodes'>
            <td colspan='1' align='center''>%s</td>
            <td colspan='1' align='center''>%s</td>
            <td colspan='1' align='center''>%s</td>
            <td colspan='1' align='center''>%s</td>
            <td colspan='1' align='center''>%s</td>
            <td colspan='1' align='center''>%s</td>
        </tr>
        """
        tr = ""
        for idx, node in enumerate(nodes_info):
            tr += html_template % (idx, node["Name"], node["Status"], node["IPAddress"],
                                   node["Roles"], node["User"], node["Password"])
        return tr

    def _get_result_table_string(self, result):
        html_template = """
        <tr id='result_%d' class='result'>
            <td colspan='1' align='left' class='%s'>%s</td>
            <td colspan='1' align='center' class='%s'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>Loop: %d</td>
        </tr>
        """

        msg_template = """
        <tr id='msg_%d' class='output'>
            <td colspan='1' align='left' class='%s'>Message</td>
            <td colspan='3' align='left' class='%s'>%s</td>
        </tr>
        """

        tr = ""
        sorted_result = self.sort_result(result.result)
        for cid, (cls, cls_results) in enumerate(sorted_result):
            np = nf = ne = ns = 0
            for n, t, o, e, d, l in cls_results:
                name = t.id().split('.')[-1]
                doc = t.shortDescription() or ""
                desc = doc and ('%s: %s' % (name, doc)) or name
                output = saxutils.escape(o + e)
                if n == 0:
                    np += 1
                    style = 'passCase'
                elif n == 1:
                    nf += 1
                    style = 'failCase'
                elif n == 2:
                    ne += 1
                    style = 'errorCase'
                elif n == 3:
                    ns += 1
                    style = 'skipCase'
                elif n == 4:
                    np += 1
                    style = 'passCase'
                else:
                    style = 'none'

                tr += html_template % (cid, style, desc, style, STATUS[n], d, l)
                if output:
                    tr += msg_template % (cid, style, style, output)
        return tr

    def generate_report(self, result):
        total_count = sum([
            result.success_count,
            result.failure_count,
            result.error_count,
            result.skipped_count]
        )
        attr = self._get_attributes_table_string(result)
        results = self._get_result_table_string(result)
        nodes = self._get_nodes_table_string(self.test_nodes)
        output = REPORT_TEMPLATE % dict(
            Title=self.title,
            Generator=__author__,
            Description=attr,
            Nodes=nodes,
            Total=str(total_count),
            Pass=str(result.success_count),
            Fail=str(result.failure_count),
            Error=str(result.error_count),
            Skip=str(result.skipped_count),
            Cancel=str(result.canceled_count),
            Passrate=self.passrate,
            Results=results
        )

        report_path_dir = os.path.dirname(self.report_path)
        if not os.path.isdir(report_path_dir):
            try:
                os.makedirs(report_path_dir)
            except OSError as e:
                raise Exception(e)
        with open(self.report_path, 'wb') as f:
            f.write(output.encode('UTF-8'))

        return True


##############################################################################
# Facilities for running tests from the command line
##############################################################################

# Note: Reuse unittest.TestProgram to launch test. In the future we may
# build our own launcher to support more specific command line
# parameters like test title, CSS, etc.
class TestProgram(unittest.TestProgram):
    """
    A variation of the unittest.TestProgram. Please refer to the base
    class for command line parameters.
    """

    def runTests(self):
        # Pick StressRunner as the default test runner.
        # base class's testRunner parameter is not useful because it means
        # we have to instantiate StressRunner before we know self.verbosity.
        if self.testRunner is None:
            self.testRunner = StressRunner()
        unittest.TestProgram.runTests(self)


main = TestProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)
