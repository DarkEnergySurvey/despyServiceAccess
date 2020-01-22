#!/usr/bin/env python3
import os
import unittest
import stat
import sys
import subprocess
from mock import patch
import despyserviceaccess.serviceaccess as serviceaccess

def getLinesFromShellCommand(command):
    "execute a shell command return stdout, stderr as two arrays of lines."
    # thow error if shell level error
    p = subprocess.Popen(command, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    p.wait()
    if p.returncode != 0:
        for l in p.stderr.readlines():
            print(l.rstrip())
        sys.exit(p.returncode)
    stdout = [s.rstrip() for s in p.stdout.readlines()] #kill newlines
    stderr = [s.rstrip() for s in p.stderr.readlines()]
    return (stdout, stderr)

def protect_file(f):
    """ Protect service access file according to DESDM_3"""
    os.chmod(f, (0xffff & ~(stat.S_IROTH | stat.S_IWOTH | stat.S_IRGRP | stat.S_IWGRP )))

class test_db_section2(unittest.TestCase):
    """
    make a file that is "complete" that is a file with...
       ... all defaults supplied
       ....keywords in various cases
       ... whole line comments
       ... whole line comments with # precesed by spaces
       ... comments after space after values
       ... comments glued onto values
       ... repeated keyword (last repetition "wins"
    """
    @classmethod
    def setUpClass(cls):
        cls.text = """
;
;  initial comments in file
;comment line with comment marker not in column 1 not allowed
;

[db-maximal]
USER=maximal_user
PASSWD  =   maximal_passwd
name    =   maximal_name
Sid     =   maximal_sid
type    =   POSTgres
server  =   maximal_server

[db-minimal]
USER    =   Minimal_user
PASSWD  =   Minimal_passwd
name    =   Minimal_name
sid     =   Minimal_sid
server  =   Minimal_server

[db-extra]
serverr = sevrver

[db-empty]
; empty section
"""
        cls.filename = "wellformed.ini"
        open(cls.filename, "w").write(cls.text)
        protect_file(cls.filename)
        cls.maximal = serviceaccess.parse(cls.filename, "db-maximal", "dB")
        cls.minimal = serviceaccess.parse(cls.filename, "db-minimal", "db")
        cls.empty = serviceaccess.parse(cls.filename, "db-empty", "db")
        cls.extra = serviceaccess.parse(cls.filename, "db-extra", "db")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.filename)

    def test_python_maximal_keys(self):
        """  test database with all keys specified"""
        self.assertEqual(self.maximal["user"], "maximal_user")
        self.assertEqual(self.maximal["passwd"], "maximal_passwd")
        self.assertEqual(self.maximal["type"], "postgres")
        self.assertEqual(self.maximal["name"], "maximal_name")
        self.assertEqual(self.maximal["sid"], "maximal_sid")
        self.assertEqual(self.maximal["port"], "5432")
        self.assertEqual(self.maximal["server"], "maximal_server")

    def test_python_maximal_assert(self):
        """ Test that checkign a proper file throws no errors """
        serviceaccess.check(self.maximal, "db")

    def test_python_minimal(self):
        """ Test that a db file wit hminimal keys gives full informaion.

        also various tests related to case:
          -- fetch by key is case blind .e.g. lower case works.
          -- all values are fetched case-preserving...
          -- that valuse are case preserving (expect for db_type)
          -- ... except db_type is retured stanardized to lower case.
        """
        self.assertEqual(self.minimal["user"], "Minimal_user")
        self.assertEqual(self.minimal["passwd"], "Minimal_passwd")
        self.assertEqual(self.minimal["type"], "oracle")
        self.assertEqual(self.minimal["name"], "Minimal_name")
        self.assertEqual(self.minimal["port"], "1521")

    def test_SHELL_section_via_env_good(self):
        " test that the SHELL API can obtain section from the environment"""
        section = "db-minimal"
        cmd = '(export DES_DB_SECTION=%s; serviceAccess  -t db -f %s "%%(%s)s")' % (
            section, self.filename, "meta_section")
        self.assertEqual(getLinesFromShellCommand(cmd)[0][0].decode(), section)


    def test_python_minimal_assert(self):
        """ test that check function passed a clean file"""
        serviceaccess.check(self.minimal, "db")


class TestSectionsFromEnv(unittest.TestCase):
    """
    test that we can find tag-specific sections from the environment.
    """
    @classmethod
    def setUpClass(cls):
        cls.text = """

[db-minimal]
key  =     akey
"""
        cls.filename = ".desservices.ini"
        cls.section = "db-minimal"
        open(cls.filename, "w").write(cls.text)
        protect_file(cls.filename)
        if "DES_DB_SECTION" in os.environ:
            del os.environ["DES_DB_SECTION"]

    @classmethod
    def tearDownClass(cls):
        if "DES_DB_SECTION" in os.environ:
            del os.environ["DES_DB_SECTION"]
        #os.unlink(self.filename)

    def test_via_env_good(self):
        """test python gettion section form the environment"""
        os.environ["DES_DB_SECTION"] = self.section
        _ = serviceaccess.parse(self.filename, None, "db")
        _ = serviceaccess.parse(self.filename, "", "db")

    def test_via_env_bad(self):
        """ test that fault arises when environment names section not in teh file"""
        os.environ["DES_DB_SECTION"] = "some-non-existing section"
        import configparser
        assert_fired = False
        try:
            serviceaccess.parse(self.filename, None, "db")
        except configparser.NoSectionError:
            assert_fired = True
        self.assertTrue(assert_fired)

    def test_with_env_bad_and_filename_good(self):
        """test that passed in file name trumps environment"""
        os.environ["DES_SERVICES"] = "no/file/here"
        serviceaccess.parse(self.filename, self.section, "db")

    def test_with_no_file_HOME(self):
        """ test errors is raise if HOME in error"""
        os.environ["HOME"] = "no/file/here"
        with self.assertRaises(IOError):
            serviceaccess.parse(None, self.section, "db")

    def test_HOME(self):
        """ test file in HOME area is found in python library"""
        os.environ["HOME"] = "./"
        d = serviceaccess.parse(None, self.section, "DB")
        self.assertEqual(d['key'], 'akey')


class TestBadPermissions(unittest.TestCase):
    """
    test that we find a file (in wasy we've not tested before....
    ... Can open when file "" but environment good
    ... Can open when file good but environment bad
    ... Cannot open when filename bad but env good
    ... cnoot open when file bad and env bad
    """
    @classmethod
    def setUpClass(cls):
        cls.text = """
[minimal]
key  =     akey
"""
        cls.filename = "nameresolution.desdm"
        cls.section = "minimal"
        open(cls.filename, "w").write(cls.text)
        os.chmod(cls.filename, 0xffff)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.filename)

    def test_detect_permission(self):
        """ test python API detect mal formed permissions """
        d = serviceaccess.parse(self.filename, self.section, "DB")
        try:
            serviceaccess.check(d, "db")
        except serviceaccess.ServiceaccessException:
            pass

class TestCornerCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = """
;
;  initial comments in file
;comment line with comment marker not in column 1 not allowed
;

[db-maximal]
PASSWD  =   maximal_passwd
name    =   maximal_name
Sid     =   maximal_sid
type    =   POSTgres
blah    =   blah
server  =   maximal_server

[db-minimal]
USER    =   Minimal_user
PASSWD  =   Minimal_passwd
name    =   Minimal_name
sid     =   Minimal_sid
server  =   Minimal_server

[db-extra]
serverr = sevrver

[db-empty]
; empty section
"""
        cls.filename = "wellformed.ini"
        open(cls.filename, "w").write(cls.text)
        protect_file(cls.filename)

    def test_Exception(self):
        msg = "Test of ServiceacessException"
        try:
            raise serviceaccess.ServiceaccessException(msg)
        except serviceaccess.ServiceaccessException as ex:
            self.assertTrue(msg in str(ex))
        else:
            self.assertFalse(True)

    def test_badSection(self):
        try:
            serviceaccess.parse(self.filename, None, "dB")
        except serviceaccess.ServiceaccessException as ex:
            self.assertTrue('faulty' in str(ex))
        else:
            self.assertFalse(True)

    def test_badFileNameWithRetry(self):
        with self.assertRaises(IOError):
            serviceaccess.parse('blah', 'db-sec', 'db', True)

    def test_notDb(self):
        self.minimal = serviceaccess.parse(self.filename, "db-minimal")

    def test_python_maximal_assert(self):
        """ Test that checkign a proper file throws no errors """
        with self.assertRaises(serviceaccess.ServiceaccessException):
            serviceaccess.check(serviceaccess.parse(self.filename, 'db-maximal', "db"), 'db')

    def testbadFileNameWithProcessError(self):
        with patch('despyserviceaccess.serviceaccess.subprocess.Popen', side_effect=Exception()):
            with self.assertRaises(IOError):
                serviceaccess.parse('blah', 'db-sec', 'db', True)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.filename)

if __name__ == '__main__':
    unittest.main()
