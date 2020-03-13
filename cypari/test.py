from __future__ import print_function
import doctest, re, getopt, sys
from . import tests
from . import _pari
from ._pari import Pari
import sys
if sys.version_info.major == 2:
    from . import py2tests
else:
    from . import py3tests

cpu_width = '64bit' if sys.maxsize > 2**32 else '32bit'

class DocTestParser(doctest.DocTestParser):

    def parse(self, string, name='<string>'):
        # Remove tests for the wrong architecture
        regex32 = re.compile(r'(\n.*?)\s+# 32-bit\s*$', re.MULTILINE)
        regex64 = re.compile(r'(\n.*?)\s+# 64-bit\s*$', re.MULTILINE)
        if cpu_width == '64bit':
            string = regex32.sub('', string)
            string = regex64.sub('\g<1>\n', string)
        else:
            string = regex64.sub('', string)
            string = regex32.sub('\g<1>\n', string)
        # Remove tests for the wrong Python
        regex_py2 = re.compile(r'(\n.*?)\s+# Py2\s*$', re.MULTILINE)
        regex_py3 = re.compile(r'(\n.*?)\s+# Py3\s*$', re.MULTILINE)
        if sys.version_info.major == 2:
            string = regex_py3.sub('', string)
            string = regex_py2.sub('\g<1>\n', string)
        else:
            string = regex_py2.sub('', string)
            string = regex_py3.sub('\g<1>\n', string)
        # Remove tests with random results
        regex_random = re.compile('\n[^#^\n]*# random.*\n[^\n]*[^\n]*',
                                  re.MULTILINE)
        string = regex_random.sub('', string)
        # Remove deprecation warnings in the output
        string = re.sub('[ ]*doctest:...:[^\n]*\n', '', string)
        # Enable sage tests
        string = re.sub('sage:', '>>>', string)
        string = re.sub('\.\.\.\.:', '...', string)
        # Remove lines containing :: which confuse doctests
        string = re.sub(' ::', '                  ', string)
        return doctest.DocTestParser.parse(self, string, name)

extra_globals = dict([('pari', _pari.pari)])    
modules_to_test = [
    (tests, extra_globals),
    (_pari, extra_globals),
]

# Cython adds a docstring to _pari.__test__ *only* if it contains '>>>'.
# To enable running Sage doctests, with prompt 'sage:', we need to add
# docstrings containing no '>>>' prompt to _pari.__test__ ourselves.
# Unfortunately, line numbers are not readily available to us.
for cls in (_pari.Gen, _pari.Pari):
    for key, value in cls.__dict__.items():
        docstring = getattr(cls.__dict__[key], '__doc__')
        if isinstance(docstring, str):
            if docstring.find('sage:') >= 0 and docstring.find('>>>') < 0:
                _pari.__test__['%s.%s (line 0)'%(cls.__name__, key)] = docstring

# On Windows, for some yet to be determined reason, any doctest which
# raises an exception, even an expected exception, causes the test run
# to abort with error code 3.

if sys.platform == 'win32':
    bad_tests = (
        'Pari.allocatemem', 'Pari.setrand', 'Pari.stacksize',
        'PariError.__str__', 'PariError.errdata',
        'PariError.errnum', 'PariError.errtext',
        '__test__.Gen.__call__ (line 0)',
        '__test__.Gen.__complex__ (line 0)',
        '__test__.Gen.__iter__ (line 0)',
        '__test__.Gen.bid_get_gen (line 0)',
        '__test__.Gen.change_variable_name (line 0)',
        '__test__.Gen.eval (line 0)',
        '__test__.Gen.factor (line 0)',
        '__test__.Gen.getattr (line 0)',
        '__test__.Gen.nf_get_pol (line 0)',
        '__test__.Pari._close (line 0)',
        '__test__.Pari.allocatemem (line 0)',
        '__test__.Pari.setrand (line 0)',
        'gen_to_integer')
else:
    bad_tests = (
        '__test__.Pari._close (line 0)', # unused, marked dangerous and segfaults
    )

def runtests(verbose=False):
    parser = DocTestParser()
    finder = doctest.DocTestFinder(parser=parser)
    failed, attempted = 0, 0
    for module, extra_globals in modules_to_test:
        print('Running doctests in %s:'%module.__name__)
        runner = doctest.DocTestRunner(
            verbose=verbose,
            optionflags=doctest.ELLIPSIS|doctest.IGNORE_EXCEPTION_DETAIL)
        count = 0
        for test in finder.find(module, extraglobs=extra_globals):
            if test.name.split('.', 2)[-1] in bad_tests:
                print('skipping %s'%test.name.split()[0])
                continue
            count += 1
            runner.run(test)
        result = runner.summarize()
        failed += result.failed
        attempted += result.attempted
        print(result)
        print()
    print('\nAll doctests:\n   %s failures out of %s tests.' % (failed, attempted))
    return failed

if __name__ == '__main__':
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'v', ['verbose'])
        opts = [o[0] for o in optlist]
        verbose = '-v' in opts
    except getopt.GetoptError:
        verbose = False
    failed = runtests(verbose)
    sys.exit(failed)
