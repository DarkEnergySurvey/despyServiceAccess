#!/usr/bin/env python
"""
Support a service access file as described in DESDM-3


The parse functions return a dictionary of  keys in the specified
seection of the specified file.

If file or section is not specified, devfaults  are supplied in a tag-specific way
as sepcified in DESDM-3.

Check supplies chaking of entries as specified in DESDM-3


"""

import os
import time
import subprocess

class ServiceaccessException(Exception):
    "class for any file-content, + null fle name"
    def __init__(self, txt):
        Exception.__init__(self)
        self.txt = txt
    def __str__(self):
        return self.txt


expectedkeys = ("meta_section", "meta_file")
expected_db_keys = ("user", "passwd", "type", "port", "server", "name", "sid", "meta_section", "meta_file", "service")

def parse(file_name, section, tag=None, retry=False):
    """parse a serviceaccess file, return a dictionary of keys  section supplimented by defaults indicated by tag

    provide two extra dictionary entries,
         meta_file     indicating the file actually used.
         meta_section  indicating the section actually used. """

    if not file_name:
        file_name = os.getenv("DES_SERVICES")
    if not file_name:
        file_name = os.path.join(os.getenv("HOME"), ".desservices.ini")
    if not section and tag:
        section = os.getenv("DES_%s_SECTION" % tag.upper())
    if not section:
        raise ServiceaccessException('faulty section: %s' % section)

    # config parser throws "no section error" if file does not exist....
    # ... That's Confusing. so do an open to get a more understandable error.
    # to allow for automounting filesystems, retry on failures
    maxtries = 1
    if retry:
        maxtries = 5
    trycnt = 0
    delay = 30
    success = False
    exc = None
    while not success and trycnt <= maxtries:
        trycnt += 1
        try:
            open(file_name)
            success = True
        except IOError as exc:
            if trycnt < maxtries:
                print "IOError: %s" % exc
                print "Sleeping for %s seconds and retrying" % delay
                try:
                    # try triggering automount
                    process = subprocess.Popen(['ls', '-l', file_name], shell=False,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT)
                    process.wait()
                    #print process.communicate()
                except Exception:
                    pass
                time.sleep(delay)
            else:
                raise


    import ConfigParser
    c = ConfigParser.RawConfigParser()
    c.read(file_name)
    d = {}
    [d.__setitem__(key, value) for (key, value) in c.items(section)]
    d["meta_file"] = file_name
    d["meta_section"] = section

    if tag and tag.lower() == "db":
        d = _process_db(d)
    return d

def check(d, tag=None):
    "raise execption if file or indicated keys inconsistent with DESDM-3."
    import stat
    permission_faults = []
    permission_checks = (("other_read", stat.S_IROTH), ("other_write", stat.S_IWOTH),
                         ("group_write", stat.S_IWGRP))
    permissions = os.stat(d["meta_file"])[0]
    for (text, bit) in permission_checks:
        if permissions & bit:
            permission_faults.append(text)
    if permission_faults:
        raise ServiceaccessException("faulty permissions : %s " % (permission_faults))
    if tag and tag.lower() == "db":
        _check_db(d)

    return

def _process_db(d):
    "suppliment db section supplimented with DB defaults."
    d.setdefault("type", "oracle")
    d["type"] = d["type"].lower()
    d.setdefault("sid", None)
    d.setdefault("name", None)
    if d["type"] == "oracle":
        d.setdefault("port", "1521")
    if d["type"] == "postgres":
        d.setdefault("port", "5432")
    return d

def _check_db(d):
    "suppliment chack with  DB specific rules."
    missing = []
    extra = []
    _ = d["meta_file"]
    _ = d["meta_section"]
    for key in ("user", "passwd", "type", "port", "server"):
        if key not in d.keys():
            missing.append(key)
    for key in d.keys():
        if key not in expected_db_keys:
            extra.append(key)
    check(d)
    if missing or extra:
        raise ServiceaccessException("faulty keys : %s   %s" % (missing, extra))
    return
