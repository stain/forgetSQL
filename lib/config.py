#!/usr/bin/env python

import sys
import os
import ConfigParser

# magic to get the right directories.
# assumes that this binary is in some /blapp/blupp/bin/wrapper
# and that libraries are in /blapp/blupp/lib.

bindir = os.path.dirname(sys.argv[0])
rootdir = os.path.abspath(os.path.join(bindir, '..'))
libdir = os.path.join(rootdir, 'lib')
etcdir = os.path.join(rootdir, 'etc')
testdir = os.path.join(rootdir, 'test')

conf = ConfigParser.ConfigParser()
conf.read(os.path.join(etcdir, 'daddyQ.conf'))

if libdir not in sys.path:
    sys.path.append(libdir)

# prepare database    
import database
