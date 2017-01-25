import os
import sys
import time
import json
import pytest


diff_report = None


class DiffReport(object):

    def __init__(self, config):
        from _pytest.config import create_terminal_writer
        self.filename = '.last-run'
        self.results = {}
        self._tw = create_terminal_writer(config, sys.stdout)

    def record_result(self, name, outcome):
        self.results[name] = outcome

    def write_to_file(self):
        if self.results != self.get_last_run():
            with open(self.filename, 'w') as f:
                f.write(json.dumps(self.results).rstrip() + '\n')

    def get_last_run(self):
        try:
            with open(self.filename) as f:
                return json.load(f)
        except IOError:
            pass
        return {}

    def diff_with_run(self, old):
        a = old
        b = self.results

        diffs = {}
        unhandled = set(b)

        for key, value in a.iteritems():
            if value != b.get(key):
                diffs[key] = (value, b.get(key))
            unhandled.discard(key)

        for key in unhandled:
            diffs[key] = (None, b[key])

        def _write_status(status):
            if status == 'passed':
                self._tw.write('PASSED', green=True)
            elif status == 'failed':
                self._tw.write('FAILED', red=True)
            elif status == 'skipped':
                self._tw.write('SKIPPED', yellow=True)
            elif status is None:
                self._tw.write('MISSING', cyan=True)
            else:
                self._tw.write(status.upper())

        new_failed = 0
        new_passed = 0

        self._tw.line()
        if not diffs:
            self._tw.sep('~', 'NO CHANGES SINCE LAST RUN')
            return

        self._tw.sep('~', 'CHANGES SINCE LAST RUN FOUND')
        for key, (old, new) in sorted(diffs.items()):
            self._tw.write(key.split('::')[-1] + ' ')
            _write_status(old)
            self._tw.write(' -> ')
            _write_status(new)
            self._tw.line()
            if new == 'failed':
                new_failed += 1
            elif new == 'passed':
                new_passed += 1

        self._tw.sep('~', 'new passed: %d, new failed: %d' %
                     (new_passed, new_failed))


def pytest_configure(config):
    global diff_report
    diff_report = DiffReport(config)


def pytest_unconfigure(config):
    old_run = diff_report.get_last_run()
    diff_report.write_to_file()
    diff_report.diff_with_run(old_run)


from _pytest import terminal
print(dir(terminal))


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call':
        diff_report.record_result(item.nodeid, rep.outcome)


@pytest.fixture(scope='module')
def res_path():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, 'res')


@pytest.fixture(scope='function')
def driver(request):
    from symsynd.driver import Driver
    rv = Driver()
    request.addfinalizer(rv.close)
    return rv
