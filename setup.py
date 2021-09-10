from distutils.core import setup


DEPENDENCIES = ['click']


setup(name='p2p_fileshare',
      version='1.0',
      description='p2p file sharing application',
      author='Ron Geva, Tal Persia',
      author_email='coolron54@gmail.com',
      packages=['p2p_fileshare'],
      install_requires=DEPENDENCIES
)
