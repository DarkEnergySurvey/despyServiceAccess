import distutils
from distutils.core import setup
import os,sys

def test_services():

    # Now we perform some testing
    unittestargs="--quiet"

    here = os.getcwd()
    os.chdir("tests")
    cmd = "./test_serviceaccess.py %s"  % unittestargs
    print cmd
    os.system(cmd)
    os.chdir(here)
    return

# The main call
setup(name='despyServiceAccess',
      version ='2.0.2',
      license = "GPL",
      description = "Support a service access file as described in DESDM",
      author = "The National Center for Supercomputing Applications (NCSA)",
      packages = ['despyserviceaccess'],
      package_dir = {'': 'python'},
      scripts = ['bin/serviceAccess'],
      )

test_services()


