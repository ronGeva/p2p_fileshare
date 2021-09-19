from distutils.core import setup
from setuptools import find_packages


DEPENDENCIES = ['filelock']


setup(name='p2p_fileshare',
      version='1.0',
      description='p2p file sharing application',
      author='Ron Geva, Tal Persia',
      author_email='coolron54@gmail.com',
      packages=find_packages(),
      install_requires=DEPENDENCIES
)
