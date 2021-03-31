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
    from stressrunner import runner
    if __name__ == '__main__':
        runner.main()
For more customization options, instantiates a StressRunner object.
StressRunner is a counterpart to unittest's TextTestRunner. E.g.
    # output to a file
    runner = StressRunner(
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
import platform
import time
import datetime
import io
import socket
import traceback
from xml.sax import saxutils
from xml.dom import minidom
import unittest

from stressrunner import mail
from stressrunner.report import REPORT_TEMPLATE

# =============================
# --- Global
# =============================
__author__ = "tao.xu"
__version__ = "1.5.1"
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
PY2 = sys.version_info[0] == 2
# sys.setrecursionlimit(100000)

TESTER = __author__
REPORT_TITLE = "Test Report"
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


def seconds_to_string(seconds):
    # str(stop_time - start_time).split('.')[0]
    return "{:0>8}".format(str(datetime.timedelta(seconds=seconds)))


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
    elif isinstance(value, (datetime.date, datetime.datetime)):
        value = value.isoformat()

    # make bools into true/false strings
    elif isinstance(value, bool):
        value = str(value).lower()

    # don't decode bytestrings
    elif isinstance(value, bytes):
        return value

    # encode strings to utf-8
    # Python2 basestring,  --> (str, unicode)
    string_types = basestring if PY2 else str, bytes
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

    msg = "[{0:^6}] {1} --Loop: {2} --ElapsedTime: {3}"

    def __init__(self, logger, descriptions=None, verbosity=2, fail_exit=True):
        """
        _TestResult inherit from unittest TestResult
        :param logger: default is logging.get_logger()
        :param verbosity: 1-dots, 2-showStatus, 3-showAll
        :param fail_exit: exit all test if any tc failed/error/canceled
        """
        super(_TestResult, self).__init__()
        self.logger = logger
        self.descriptions = descriptions
        self.verbosity = verbosity
        self.fail_exit = fail_exit
        self.tc_loop_limit = 1

        self.showAll = verbosity >= 3
        self.showStatus = verbosity == 2
        self.dots = verbosity <= 1

        self.stdout0 = None
        self.stderr0 = None
        self._stdout_buffer = None
        self._stderr_buffer = None
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self.outputBuffer = ''

        # extend more results
        self.successes = []
        self.canceled = []
        self.all = []  # (status, test, output, stack_trace, elapsed_time, loop)
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.canceled_count = 0

        self.ts_loop = 1
        self.tc_loop = 0
        self.tc_start_time = datetime.datetime.now()  # test case start time
        self.ts_start_time = datetime.datetime.now()  # test suite start time

    @staticmethod
    def get_description(test):
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
        if len(self.all) > 0:
            self.all.pop(-1)

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

        tc_stop_time = datetime.datetime.now()
        tc_elapsedtime = (tc_stop_time - self.tc_start_time).seconds
        ts_elapsedtime = (tc_stop_time - self.ts_start_time).seconds
        for test_item, err in (self.errors + self.failures):
            if test_item == test:
                output_info += "{test_info}:".format(test_info=test)

        return output_info, tc_elapsedtime, ts_elapsedtime

    def startTest(self, test):
        self.logger.info("[START ] {0} -- Loop: {1}".format(str(test), self.ts_loop))
        self.all.append((4, test, '', '', '', self.ts_loop))
        self.tc_start_time = datetime.datetime.now()
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
        sn = 0
        status = STATUS[sn]
        self.tc_loop += 1
        self.success_count += 1
        self.successes.append((test, ''))
        unittest.TestResult.addSuccess(self, test)

        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.all.append((sn, test, output, '', tc_elapsedtime, self.ts_loop))
        if self.showAll:
            self.logger.info(self.msg.format(status, str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.info(status)
        elif self.dots:
            self.logger.info("\n.")
        else:
            pass

        # calculate retry or not
        if (self.tc_loop_limit == 0) or (self.tc_loop_limit > self.tc_loop):
            retry_flag = True
        else:
            retry_flag = False

        # recursive retry test
        if retry_flag:
            test = copy.copy(test)
            self.tc_start_time = datetime.datetime.now()
            test(self)
        else:
            self.tc_loop = 0  # update for next test case loop=0

    def addError(self, test, err):
        sn = 2
        status = STATUS[sn]
        self.failure_count += 1
        unittest.TestResult.addError(self, test, err)
        _, str_e = self.errors[-1]
        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.all.append((sn, test, output, str_e, tc_elapsedtime, self.ts_loop))
        if self.showAll:
            self.logger.critical(self.msg.format(status, str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.critical(status)
        else:
            self.logger.critical("\nE")
        self.tc_loop = 0
        if self.fail_exit:
            self.logger.warning("Stop all test because test {} meet Error ...".format(test))
            self.stop()

    def addFailure(self, test, err):
        sn = 1
        status = STATUS[sn]
        self.failure_count += 1
        unittest.TestResult.addFailure(self, test, err)
        _, str_e = self.failures[-1]
        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.all.append((sn, test, output, str_e, tc_elapsedtime, self.ts_loop))
        if self.showAll:
            self.logger.critical(self.msg.format(status, str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.critical(status)
        else:
            self.logger.critical("\nF")
        self.tc_loop = 0
        if self.fail_exit:
            self.logger.warning("Stop all test because test {} FAILED ...".format(test))
            self.stop()

    def addSkip(self, test, reason):
        sn = 3
        status = STATUS[3]
        self.skipped_count += 1
        unittest.TestResult.addSkip(self, test, reason)
        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.all.append((sn, test, output, reason, tc_elapsedtime, self.ts_loop))
        if self.showAll:
            self.logger.warning(self.msg.format(status, str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.warning(status)
        else:
            self.logger.warning("\nS")
        self.tc_loop = 0

    def add_canceled(self):
        sn = 4
        status = STATUS[sn]
        self.canceled_count += 1
        if len(self.all) > 0:
            test = self.all[-1][1]
        else:
            test = ''
        self.all.pop(-1)
        self.canceled.append((test, 'Canceled'))

        output, tc_elapsedtime, ts_elapsedtime = self._restore_output(test)
        self.all.append((sn, test, output, '', tc_elapsedtime, self.ts_loop))
        if self.showAll:
            self.logger.info(self.msg.format(status, str(test), self.ts_loop, tc_elapsedtime))
            self.logger.info("Total Elapsedtime: {0}".format(ts_elapsedtime))
        elif self.showStatus:
            self.logger.info(status)
        elif self.dots:
            self.logger.info("\n.")
        else:
            pass
        self.tc_loop = 0
        if self.fail_exit:
            self.logger.warning("Stop all test because test {} CANCELED ...".format(test))
            self.stop()

    def print_error_list(self, flavour, errors):
        for test, err in errors:
            self.logger.error("{0}: {1}\n{2}".format(flavour, self.get_description(test), err))

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
    separator1 = '=' * 70
    separator2 = '-' * 70

    def __init__(self, report_html=None, result_xml=None, logger=None, loop=1, verbosity=2,
                 tester=TESTER, test_version=None, description=None, report_title=REPORT_TITLE,
                 test_env=None, test_nodes=None):
        """
        Stress runner
        Args:
            report_html: default ./report.html
            logger:
            loop: the max test loop
            verbosity: 2: show All
            :param tester:
            :param test_version:
            :param description:
            :param report_title:
            :param test_env:
            :param test_nodes:
        """

        if test_nodes is None:
            test_nodes = []
        if test_env is None:
            test_env = {}
        self.report_html = report_html or self.default_report_html
        self.result_xml = result_xml or self.default_result_xml
        self.logger = logger or self.default_logger
        self.loop = loop
        self.verbosity = verbosity
        self.save_last_result = True

        # --------------- Info for display on report.html ---------------
        # test info
        self.tester = tester
        self.test_desc = description
        self.test_version = test_version
        self.report_title = report_title
        # test env info
        self.test_env = test_env  # dict with key:value
        self.test_nodes = test_nodes  # dict list, item.keys: Name, Status, IPAddress, Roles, User, Password

        # --------------- test status ---------------
        self.start_time = datetime.datetime.now()
        self.stop_time = ''
        self.elapsedtime = ''
        self.passrate = ''
        self.summary = ''  # eg: "ALL 1, PASS 1, Passing rate: 100%"

    @property
    def default_logger(self):
        log_format = '%(asctime)s %(name)s %(levelname)s: %(message)s'
        sr_logger = logging.getLogger('StressRunner')
        coloredlogs.install(logger=sr_logger, level=logging.DEBUG, fmt=log_format)
        return sr_logger

    @property
    def default_report_html(self):
        return os.path.join(os.getcwd(), 'report.html')

    @property
    def default_result_xml(self):
        return os.path.join(os.getcwd(), 'result.xml')

    def send_mail(self, m_from, m_to, host, user, password, port, tls):
        if not m_to:
            return True
        self.logger.info("> Send mail to {} ...".format(m_to))

        with open(self.report_html, 'rb') as f:
            content = f.read()

        attachments = []
        log_path = self.report_html.replace('.html', '.log')
        if os.path.getsize(log_path) < 2048 * 1000:
            attachments.append(log_path)
        # attachments.append(self.report_path)

        mail.send_mail(self.report_title, content, m_from, m_to, host, user, password, port, tls, attachments)
        return True

    def run(self, test):
        """
        Run the given test case or test suite
        :param test: unittest.testSuite
        :return:
        """
        _result = _TestResult(self.logger, self.verbosity)
        test_status = STATUS[2]  # 'ERROR'
        retry_flag = True
        try:
            while retry_flag:
                # retry test suite by Loop
                running_test = copy.deepcopy(test)
                self.logger.info("Test Case List:")
                for _test in running_test._tests:
                    self.logger.info(_test)

                running_test(_result)
                _result.ts_loop += 1
                fail_count = _result.failure_count + _result.error_count
                test_status = STATUS[1] if fail_count > 0 else STATUS[0] # 0-'PASSED', 1-'FAILED'
                del running_test

                if fail_count > 0:
                    retry_flag = False
                elif self.loop == 0 or self.loop >= _result.ts_loop:
                    retry_flag = True
                else:
                    retry_flag = False
        except KeyboardInterrupt:
            self.logger.info("Script stoped by user --> ^C")
            if (_result.failure_count + _result.error_count) > 0:
                test_status = STATUS[1]  # 'FAILED'
            elif _result.success_count <= 0:
                test_status = STATUS[4]  # 'CANCELED'
            else:
                test_status = STATUS[0]  # 'PASSED'
            _result.add_canceled()
        except Exception as e:
            self.logger.error(e)
            self.logger.error('{err}'.format(err=traceback.format_exc()))
            failed_elapsed_time = (datetime.datetime.now() - _result.tc_start_time).seconds
            sn, t, o, e, d, lp = _result.all[-1]
            if sn == 4:
                _result.all.pop(-1)
                _result.all.append((2, t, o, e, failed_elapsed_time, lp))
        finally:
            self.logger.info(_result)
            if _result.testsRun < 1:
                return _result
            self.stop_time = datetime.datetime.now()
            self.elapsedtime = (self.stop_time - self.start_time).seconds
            self.report_title = test_status + ": " + self.report_title
            self.generate_report(_result)
            self.generate_xml(_result)

            if _result.all:
                self._print_result(_result)
            else:
                for _test in test._tests:
                    self.logger.info(_test)

            return _result, test_status

    @staticmethod
    def _sort_result(result_list):
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

    def _print_result(self, result):
        self.logger.info(self.separator1)
        # result.print_errors()
        for res in result.all:
            msg = "{stat} - {tc} - Loop: {loop} - Elapsed: {elapsed}" \
                .format(stat=STATUS[res[0]], tc=res[1], loop=res[5], elapsed=seconds_to_string(res[4]))
            self.logger.info(msg)
            err_failure = res[3].strip('\n')
            if err_failure:
                self.logger.error(err_failure)
        self.logger.info(self.separator2)
        total_count = sum([
            result.success_count,
            result.failure_count,
            result.error_count,
            result.skipped_count,
            result.canceled_count])
        self.logger.info("Pass: {0}".format(result.success_count))
        self.logger.info("Fail: {0}".format(result.failure_count))
        self.logger.info("Error: {0}".format(result.error_count))
        self.logger.info("Skipped: {0}".format(result.skipped_count))
        self.logger.info("Canceled: {0}".format(result.canceled_count))
        self.logger.info("Total: {0}".format(total_count))
        self.logger.info('Time Elapsed: {0}'.format(seconds_to_string(self.elapsedtime)))
        self.logger.info('JunitXml Path: {0}'.format(self.result_xml))
        self.logger.info('ReportHtml Path: {0}'.format(self.report_html))
        self.logger.info('Test Location: {0}({1})'.format(self.local_hostname, self.local_ip))
        self.logger.info(self.separator1)
        return True

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
            'Elapsed': seconds_to_string(self.elapsedtime),
            'Summary': self.summary,
            'Location': '{0}({1})'.format(self.local_hostname, self.local_ip),
            'Workspace': os.getcwd(),
            'Report': self.report_html,
            'Command': 'python ' + ' '.join(sys.argv),
            'Python': platform.python_version(),
        }
        if self.test_desc:
            attr = dict(attr, **({'Description': self.test_desc}))

        return dict(attr, **self.test_env)

    def _get_attributes_table_string(self, result):
        """
        get attributes table_string
        """
        att_template = """
        <tr id='attr_%d' class='attr'>
            <td colspan='1' align='left' width='15%%'>%s</td>
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
            "Roles": "Executor",
            "User": "root",
            "Password": "********",
            "OS": platform.system(),
        })
        html_template = """
        <tr id='node_%d' class='nodes'>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
        </tr>
        """
        tr = ""
        for idx, node in enumerate(nodes_info):
            tr += html_template % (idx, node["Name"], node["Status"], node["IPAddress"],
                                   node["Roles"], node["User"], node["Password"], node["OS"])
        return tr

    def _get_result_table_string(self, result):
        html_template = """
        <tr id='result_%d' class='%s'>
            <td colspan='1' align='left'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%s</td>
            <td colspan='1' align='center'>%d</td>
        </tr>
        """

        msg_template = """
        <tr id='msg_%d' class='%s'>
            <td colspan='1' align='left'>Message</td>
            <td colspan='3' align='left'><pre>%s</pre></td>
        </tr>
        """

        tr = ""
        sorted_result = self._sort_result(result.all)
        for cid_1, (cls, cls_results) in enumerate(sorted_result):
            np = nf = ne = ns = 0
            for cid_2, (n, t, o, e, d, l) in enumerate(cls_results):
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
                cid = int("{0}{1}".format(cid_1, cid_2))
                tr += html_template % (cid, style, desc, STATUS[n], seconds_to_string(d), l)
                if output:
                    tr += msg_template % (cid, style, output)
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
        title_color = "h_red" if STATUS[1] in self.report_title or STATUS[2] in self.report_title else "h_green"
        output = REPORT_TEMPLATE % dict(
            Title=self.report_title,
            TitleColor=title_color,
            Generator=__author__,
            Environment=attr,
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

        report_path_dir = os.path.dirname(self.report_html)
        if not os.path.isdir(report_path_dir):
            try:
                os.makedirs(report_path_dir)
            except OSError as e:
                raise Exception(e)
        with open(self.report_html, 'wb') as f:
            f.write(output.encode('UTF-8'))

        return True

    def generate_xml(self, result):
        total_count = sum([
            result.success_count,
            result.failure_count,
            result.error_count,
            result.skipped_count,
            result.canceled_count])
        impl = minidom.getDOMImplementation()
        doc = impl.createDocument(None, 'testsuites', None)
        rootElement = doc.documentElement
        # rootElement = doc.createElement('testsuites')
        ts_element = doc.createElement('testsuite')
        ts_element.setAttribute('name', 'test')
        ts_element.setAttribute('errors', str(result.error_count))
        ts_element.setAttribute('failures', str(result.failure_count))
        ts_element.setAttribute('skipped', str(result.skipped_count))
        ts_element.setAttribute('success', str(result.success_count))
        ts_element.setAttribute('canceled', str(result.canceled_count))
        ts_element.setAttribute('tests', str(total_count))
        ts_element.setAttribute('time', str(self.elapsedtime))
        # ts_element.setAttribute('timestamp', str(time.strftime("%Y-%m-%d%H%:M%:S", time.localtime())))
        ts_element.setAttribute('timestamp', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        ts_element.setAttribute('hostname', '{0}({1})'.format(self.local_hostname, self.local_ip))
        # ts_element.appendChild(doc.createTextNode(''))
        for res in result.all:
            # self.logger.debug(res)
            tc_element = doc.createElement('testcase')
            tc_element.setAttribute('classname', "%s.%s" % (res[1].__class__.__module__, res[1].__class__.__qualname__))
            tc_element.setAttribute('name', str(res[1]._testMethodName))
            tc_element.setAttribute('time', str(res[4]))
            # tc_element.appendChild(doc.createTextNode(''))

            if res[0] == 3:  # skiped
                skiped_element = doc.createElement('skiped')
                skiped_element.setAttribute('message', res[3])  # reason
                # skiped_element.appendChild(doc.createTextNode(''))
                tc_element.appendChild(skiped_element)
            '''
            if res[2] != "":  # has system output
                output_element = doc.createElement('system-output')
                output_element.appendChild(doc.createTextNode(res[2]))
                tc_element.appendChild(output_element)
            '''

            if res[0] in [1, 2]:  # Error, Fail
                err_failure = res[3].strip('\n')
                failure_element = doc.createElement('failure')
                failure_element.setAttribute('message', err_failure.split("\n")[-1])
                failure_element.setAttribute('type',  "Error")
                # failure_element.appendChild(doc.createTextNode(err_failure))
                tc_element.appendChild(failure_element)

            ts_element.appendChild(tc_element)
        rootElement.appendChild(ts_element)

        with open(self.result_xml, 'w') as f:
            doc.writexml(f, addindent='  ', newl='\n', encoding='utf-8')

        return True


# Facilities for running tests from the command line
class SRTestProgram(unittest.TestProgram):
    """
    A variation of the unittest.TestProgram. Please refer to the base
    class for command line parameters.

    Pick StressRunner as the default test runner.
    base class's testRunner parameter is not useful because it means
    we have to instantiate StressRunner before we know self.verbosity.
    """
    def __init__(self):
        super(SRTestProgram, self).__init__(module=None)
        self.testRunner = StressRunner()

    def runTests(self):
        unittest.TestProgram.runTests(self)


# Executing this module from the command line
if __name__ == "__main__":
    SRTestProgram()
