#!/usr/bin/env python

from distutils.core import setup
setup(name="forgetSQL",
      version="0.4",
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
      package_dir = {'': 'lib'}
     )
