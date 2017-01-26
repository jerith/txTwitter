import os.path

from setuptools import setup, find_packages


def readme():
    path = os.path.join(os.path.dirname(__file__), 'README.rst')
    return open(path, 'r').read()


setup(
    name="txTwitter",
    version="0.1.6",
    url='https://github.com/jerith/txTwitter',
    license='MIT',
    description="A Twisted-based client library for Twitter's API.",
    long_description=readme(),
    author='Jeremy Thurgood',
    author_email='firxen@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=['Twisted>=13.1.0', 'oauthlib', 'pyOpenSSL'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
