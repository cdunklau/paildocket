import os
import sys
import logging
import argparse
import subprocess
import getpass

from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from pyramid.paster import get_appsettings, setup_logging
from zope.sqlalchemy import mark_changed
import transaction

from paildocket.models import Base, User
from paildocket.security import create_password_context
from paildocket.tests import fixtures


logger = logging.getLogger(__name__)


class BaseCommand(object):
    name = None
    requires_config = True

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog=self.name)
        self.parser.add_argument('--verbose', '-v', action='store_true')
        if self.requires_config:
            self.parser.add_argument(
                '--config-uri', '-c', required=True,
                help='path to configuration file')

    def __call__(self, argv=sys.argv):
        self.configure_parser()
        args = self.parser.parse_args(argv[1:])
        if self.requires_config:
            self.config_uri = args.config_uri
            setup_logging(self.config_uri)
        self.run(args)

    def configure_parser(self):
        """Configure the `parser` attribute."""
        raise NotImplementedError

    def run(self, args):
        """
        Run the main routine given the namespace object returned by
        ``argparse.ArgumentParser.parse_args``.

        If `requires_config` is True, a `config_uri` attribute
        will be available.
        """
        raise NotImplementedError


class InitializeDatabaseCommand(BaseCommand):
    name = 'paildocket-initdb'

    def configure_parser(self):
        pass  # no config needed

    def run(self, args):
        settings = get_appsettings(self.config_uri)
        db_url = settings['sqlalchemy.url']
        db_name = make_url(db_url).translate_connect_args()['database']
        logger.info('Installing required database extensions')
        subprocess.check_call([
            'psql', '-d', db_name,
            '-c', 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
        ])
        engine = engine_from_config(settings, 'sqlalchemy.', echo=args.verbose)
        logger.info('Creating all tables')
        Base.metadata.create_all(engine)

initialize_database = InitializeDatabaseCommand()


class AddUserCommand(BaseCommand):
    # TODO eventually this should add an admin user instead
    name = 'paildocket-adduser'

    def configure_parser(self):
        pass

    def run(self, args):
        settings = get_appsettings(self.config_uri)
        engine = engine_from_config(settings, 'sqlalchemy.')
        session = sessionmaker(bind=engine)()

        bcrypt_rounds = settings.get('paildocket.password.bcrypt_rounds')
        pwctx = create_password_context(bcrypt__default_rounds=bcrypt_rounds)

        username = input('Enter username: ')
        email = input('Enter email: ')
        password = getpass.getpass()
        session.add(User(
            username=username,
            email=email,
            password_hash=pwctx.encrypt(password),
        ))
        logger.info('Creating user {0} with email {1}'.format(username, email))
        session.commit()

add_user = AddUserCommand()



# This is broken, needs reimplementation.
# This shouldn't be here anyway since it touches the test code, and fixtures
# aren't necessary outside of testing.
class ManageFixturesCommand(BaseCommand):
    name = 'paildocket-fixtures'

    def configure_parser(self):
        subparsers = self.parser.add_subparsers(
            dest='subparser_name', metavar='command')
        subparsers.required = True

        list_subcommand = subparsers.add_parser(
            'list', help='List available fixtures')

        install_subcommand = subparsers.add_parser(
            'install', help='Install a fixture')
        install_subcommand.add_argument('fixture_name')

        regen_subcommand = subparsers.add_parser(
            'regen', help='Regenerate (but do not install) a fixture')
        regen_subcommand.add_argument(
            '--indent', '-i', action='store_true',
            help='Indent the JSON output')
        regen_group = regen_subcommand.add_mutually_exclusive_group(
            required=True)
        regen_group.add_argument(
            '--all', '-a', action='store_true',
            help='Regenerate all generatable fixtures')
        regen_group.add_argument('fixture_name', nargs='?')

    def run(self, args):
        if args.subparser_name == 'list':
            print('Installable fixtures:')
            for fixture_name in fixtures.installable_fixtures:
                print('    ' + fixture_name)
            print('Generatable fixtures:')
            for fixture_name in fixtures.generatable_fixtures:
                print('    ' + fixture_name)
            sys.exit(0)
        elif args.subparser_name == 'install':
            settings = get_appsettings(self.config_uri)
            engine = engine_from_config(
                settings, 'sqlalchemy.', echo=args.verbose)
            init_sqlalchemy(engine)
            with transaction.manager as tx:
                fixtures.install_fixture(args.fixture_name)
                mark_changed(db.DBSession())
        elif args.subparser_name == 'regen':
            if args.all:
                for fixture_name in fixtures.generatable_fixtures:
                    fixtures.regenerate_fixture(
                        fixture_name, indent=args.indent)
            else:
                fixtures.regenerate_fixture(
                    args.fixture_name, indent=args.indent)
        else:
            raise Exception('Unexpected subparser name')

manage_fixtures = ManageFixturesCommand()
