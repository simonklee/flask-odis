"""
Flask-odis
---------

odis ext for flask
"""
from setuptools import setup

setup(
    name='Flask-odis',
    version='0.1.1',
    url='http://github.org/simonz05/flask-odis',
    license='BSD',
    author='Simon Klee',
    author_email='simon@simonklee.org',
    description='odis ext for flask',
    long_description=__doc__,
    packages=['flask_odis'],
    test_suite='nose.collector',
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask',
        'odis',
    ],
    tests_require=[
        'nose',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
