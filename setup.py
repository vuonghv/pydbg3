# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='pydbg3',
    version='0.0.1',
    description='A pure Python 3+ win32 debugger library',
    long_description=readme,
    author='Vuong Hoang',
    author_email='vuonghv.cs@gmail.com',
    url='https://github.com/vuonghv/pydbg3',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)

