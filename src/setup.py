#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

from platform import python_version
from setuptools import setup, find_packages


major, minor, micro = python_version().split('.')

if major != '2' or minor not in ['4', '5', '6', '7']:
    raise Exception('unsupported version of python')

requires = [
    'web.py == 0.32',
    'grinder >= 0.0.86',
    'pymongo >= 1.9'
]

if minor not in ['6', '7']:
    requires.extend([
        'simplejson == 2.0.9',
    ])


setup(
    name='pulp',
    version='0.0.129',
    description='content mangement and delivery',
    author='Jason L Connor, Mike McCune',
    author_email='jconnor@redhat.com, mmcune@redhat.com',
    url='',
    license='GPLv2+',
    packages=find_packages(),
    scripts=[
        '../bin/pulp-admin',
        '../bin/pulp-client',
        '../bin/pulp-migrate',
    ],
    include_package_data=False,
    data_files=[],
    classifiers=[
        'License :: OSI Approved :: GNU General Puclic License (GPL)',
        'Programming Language :: Python',
        'Operating System :: POSIX',
        'Topic :: Content Management and Delivery',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        'Development Status :: 3 - Alpha',
    ],
    install_requires=requires,
)

