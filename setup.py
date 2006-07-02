#!/usr/bin/env python

from distutils.core import setup

# Whyyyyyyy oh whyyy doesn't distutils do this !??
# (if you forget this - root with umask 0077 
#  will install non-readable libraries)
import os
if os.geteuid() == 0:
    os.umask(0022)

setup(name="forgetSQL",
      version="0.5.2.rc1",
      author="Stian Soiland",
      author_email="stian@soiland.no",
      url="http://forgetsql.sourceforge.net/",
      license="LGPL",
      description=
"""forgetSQL is a Python module for accessing SQL databases by creating
classes that maps SQL tables to objects, normally one class pr. SQL
table. The idea is to forget everything about SQL and just worrying
about normal classes and objects.""",
      py_modules=['forgetSQL'],
      scripts = ['bin/forgetsql-generate'],
      package_dir = {'': 'lib'},
     )
