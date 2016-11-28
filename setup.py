import os

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt'), encoding='utf-8') as f:
    CHANGES = f.read()

requires = [
    'pyramid',
    'pyramid_tm',
    'pyramid_jinja2',
    'pyramid_beaker',
    'psycopg2',
    'sqlalchemy>=1.0,<1.1',
    'zope.sqlalchemy',
    'passlib>=1.6,<1.7',
    'bcrypt',
    'deform>=0.9,<1.0',
]

classifiers = [
    "Programming Language :: Python",
    "Framework :: Pyramid",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
]

setup(
    name='paildocket',
    version='0.0',
    description='',
    long_description=README + '\n\n' + CHANGES,
    classifiers=classifiers,
    author='Colin Dunklau',
    author_email='colin.dunklau@gmail.com',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(include=['paildocket']),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = paildocket.wsgi:main
    [console_scripts]
    initialize_database = paildocket.management:initialize_database
    add_user = paildocket.management:add_user
    manage_fixtures = paildocket.management:manage_fixtures
    """,
)
