#!/usr/bin/env python

import os
from setuptools import setup, find_packages

__author__ = 'Derek Payton <derek.payton@gmail.com>'
__description__ = 'A basic CRUD admin interface for Django+MongoEngine, very similar to `django.contrib.admin`'
__license__ = 'MIT License'
__version__ = '0.1a'

## Package detection from django-registration

# Compile the list of packages available, because distutils doesn't have
# an easy way to do this.
packages, data_files = [], []
root_dir = os.path.dirname(__file__)
if root_dir:
    os.chdir(root_dir)

for dirpath, dirnames, filenames in os.walk('mongoadmin'):
    # Ignore dirnames that start with '.'
    for i, dirname in enumerate(dirnames):
        if dirname.startswith('.'): del dirnames[i]
    if '__init__.py' in filenames:
        pkg = dirpath.replace(os.path.sep, '.')
        if os.path.altsep:
            pkg = pkg.replace(os.path.altsep, '.')
        packages.append(pkg)
    elif filenames:
        prefix = dirpath[11:] # Strip "mongoadmin/" or "mongoadmin\"
        for f in filenames:
            data_files.append(os.path.join(prefix, f))

setup(
    name='django-mongoadmin',
    version=__version__,
    description=__description__,
    long_description=__description__,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        ],
    keywords='django mongoengine mongoforms mongodb',
    maintainer = 'Derek Payton',
    maintainer_email = 'derek.payton@gmail.com',
    url='https://github.com/dmpayton/django-mongoadmin',
    license=__license__,
    packages=packages,
    package_data={'mongoadmin': data_files},
    package_dir={'mongoadmin': 'mongoadmin'},
    zip_safe=False,
    )
