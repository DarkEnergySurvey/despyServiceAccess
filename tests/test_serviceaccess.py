#!/usr/bin/env python
import os
import despyserviceaccess.serviceaccess as serviceaccess
import unittest
import stat
import sys
import re
import subprocess

def getLinesFromShellCommand (command):
    "execute a shell command return stdout, stderr as two arrays of lines."
    # thow error if shell level error                                                                                                          
    p = subprocess.Popen(command, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    p.wait()
    if p.returncode !=0 : 
        for  l in  p.stderr.readlines(): print l.rstrip()
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
    def setUp(self):
        self.text = """
;
;  initial comments in file 
;comment line with comment marker not in column 1 not allowed
;

[db-maximal]
USER=maximal_user   
PASSWD  =   maximal_passwd
name    =   maximal_name_1    ; if repeated last name wins 
name    =   maximal_name      ; if repeated key, last one wins
Sid     =   maximal_sid       ;comment glued onto value not allowed   
type    =   POSTgres
server  =   maximal_server

[db-minimal]
USER    =   Minimal_user
PASSWD  =   Minimal_passwd
name    =   Minimal_name
sid     =   Minimal_sid
server  =   Minimal_server

[db-extra]
serverr = sevrver   ; example of mis-spelled keyword

[db-empty]
; empty section
"""
        self.filename = "wellformed.ini"
        open(self.filename,"w").write(self.text)
        protect_file(self.filename)
        self.maximal = serviceaccess.parse(self.filename, "db-maximal", "dB")  
        self.minimal = serviceaccess.parse(self.filename, "db-minimal", "db")  
        self.empty   = serviceaccess.parse(self.filename, "db-empty", "db")  
        self.extra   = serviceaccess.parse(self.filename, "db-extra", "db")  
        return

    def tearDown(self):
        os.unlink(self.filename)
        return

    def test_python_maximal_keys(self):
        """  test database with all keys specified""" 
        self.assertEqual(self.maximal["user"],   "maximal_user")
        self.assertEqual(self.maximal["passwd"], "maximal_passwd")
        self.assertEqual(self.maximal["type"],   "postgres")
        self.assertEqual(self.maximal["name"],   "maximal_name")
        self.assertEqual(self.maximal["sid"],    "maximal_sid")
        self.assertEqual(self.maximal["port"],   "5432")
        self.assertEqual(self.maximal["server"], "maximal_server")
        return
 
    def test_python_maximal_assert(self):
        """ Test that checkign a proper file throws no errors """
        serviceaccess.check(self.maximal,"db")
        return

    def test_python_minimal(self):
        """ Test that a db file wit hminimal keys gives full informaion.

        also various tests related to case:
          -- fetch by key is case blind .e.g. lower case works.
          -- all values are fetched case-preserving...
          -- that valuse are case preserving (expect for db_type)
          -- ... except db_type is retured stanardized to lower case.
        """
        self.assertEqual(self.minimal["user"],   "Minimal_user")
        self.assertEqual(self.minimal["passwd"], "Minimal_passwd")
        self.assertEqual(self.minimal["type"],   "oracle")
        self.assertEqual(self.minimal["name"],   "Minimal_name")
        self.assertEqual(self.minimal["port"],   "1521")

#    def test_c_good_fetch(self):
#        """ test that a good file can be accessed from C  """
#        cmd = "./test_svc_parse %%s %s %s" % ("db-minimal", self.filename) 
#        self.assertEqual(getLinesFromShellCommand (cmd % "user")[0][0],   "Minimal_user")
#        self.assertEqual(getLinesFromShellCommand (cmd % "passwd")[0][0], "Minimal_passwd")
#        self.assertEqual(getLinesFromShellCommand (cmd % "type")[0][0],   "oracle")
#        self.assertEqual(getLinesFromShellCommand (cmd % "name")[0][0],   "Minimal_name")
#        self.assertEqual(getLinesFromShellCommand (cmd % "port")[0][0],   "1521")
#        return

#    def test_C_section_via_env_good(self):
#        " test that the C API can obtain section from the environment"""
#        section = "db-minimal"
#        cmd = '(export DES_DB_SECTION=%s; ./test_svc_parse -C %s "" %s)' % (
#            section, "meta_section", self.filename) 
#        self.assertEqual(getLinesFromShellCommand (cmd)[0][0], section)

    def test_SHELL_section_via_env_good(self):
        " test that the SHELL API can obtain section from the environment"""
        section = "db-minimal"
        cmd = '(export DES_DB_SECTION=%s; serviceAccess  -t db -f %s "%%(%s)s")' % (
            section, self.filename, "meta_section") 
        self.assertEqual(getLinesFromShellCommand (cmd)[0][0], section)


    def test_python_minimal_assert(self):
        """ test that check function passed a clean file"""
        serviceaccess.check(self.minimal,"db")
        return




class TestSectionsFromEnv(unittest.TestCase):
    """
    test that we can find tag-specific sections from the environment.
    """
    def setUp(self):
        self.text = """

[db-minimal]
key  =     akey
"""
        self.filename = ".desservices.ini"
	self.section = "db-minimal"
        open(self.filename,"w").write(self.text)
	protect_file(self.filename)
        if os.environ.has_key("DES_DB_SECTION") : del os.environ["DES_DB_SECTION"] 
        return

    def tearDown(self):
        if os.environ.has_key("DES_DB_SECTION") : del os.environ["DES_DB_SECTION"]  
        #os.unlink(self.filename)
        return

    def test_via_env_good(self):
        """test python gettion section form the environment"""
        os.environ["DES_DB_SECTION"] = self.section
        d = serviceaccess.parse(self.filename, None, "db")  
        d = serviceaccess.parse(self.filename, "", "db")  

    def test_via_env_bad(self):
        """ test that fault arises when environment names section not in teh file"""
        os.environ["DES_DB_SECTION"] = "some-non-existing section"
	import ConfigParser
        assert_fired = False
	try:
            serviceaccess.parse(self.filename, None, "db") 
	except ConfigParser.NoSectionError:
            assert_fired = True
        self.assertTrue(assert_fired)
    
    def test_with_env_bad_and_filename_good(self):
        """test that passed in fiel name trumps environment"""
        os.environ["DES_SERVICES"] = "no/file/here"
	serviceaccess.parse(self.filename, self.section, "db") 

    def test_with_no_file_HOME(self):
        """ test errors is raise if HOME in error"""
        os.environ["HOME"] = "no/file/here"
	import ConfigParser
	try:
		serviceaccess.parse(None, self.section, "db") 
	except IOError:
		pass   #expect this exception 
	else:
		raise "help"

    def test_HOME(self):
        """ test file in HOME area is found in python library"""
        os.environ["HOME"] = "./"
	d = serviceaccess.parse(None, self.section, "DB")
	self.assertEqual(d['key'],'akey')

#    def test_C_HOME(self):
#        """test file is foudn in HOME in C librayr"""
#        cmd = '(export HOME=`pwd`; ./test_svc_parse -v -C meta_section aKey "")' 
#        self.assertEqual(getLinesFromShellCommand (cmd)[0][0],'aKey')



class TestBadPermissions(unittest.TestCase):
    """
    test that we find a file (in wasy we've not tested before....
    ... Can open when file "" but environment good
    ... Can open when file good but environment bad
    ... Cannot open when filename bad but env good
    ... cnoot open when file bad and env bad
    """
    def setUp(self):
        self.text = """
[minimal]
key  =     akey
"""
        self.filename = "nameresolution.desdm"
	self.section = "minimal"
        open(self.filename,"w").write(self.text)
        os.chmod(self.filename, 0xffff)
        return

    def tearDown(self):
        os.unlink(self.filename)
        return

    def test_detect_permission(self):
        """ test python API detect mal formed permissions """
        d = serviceaccess.parse(self.filename, self.section, "DB")  
	try :
		serviceaccess.check(d,"db")
	except serviceaccess.ServiceaccessException:
		pass

if __name__ == '__main__':
    unittest.main()

