import os.path

import pytest


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_INI = os.path.join(TESTS_DIR, 'unittests.ini')


@pytest.fixture(scope='session', autouse=True)
def fresh_database(request):
    """
    Drop and recreate the test database, and verify that no rows
    remain after the session.
    """
    import subprocess

    from pyramid.paster import get_appsettings
    from sqlalchemy import create_engine
    from sqlalchemy.engine.url import make_url

    from paildocket.models import Base

    settings = get_appsettings(TESTS_INI)
    # This would break pretty spectacularly if we used a different host
    # for the test database.
    db_url = settings['sqlalchemy.url']
    db_name = make_url(db_url).translate_connect_args()['database']

    subprocess.call(['dropdb', db_name])

    subprocess.check_call(['createdb', db_name])
    subprocess.check_call([
        'psql', '-d', db_name,
        '-c', 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
    ])

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    @request.addfinalizer
    def verify_clean_database():
        """Check that the database has no rows left over."""
        def psql(query):
            args = [
                'psql',
                '-d', db_name,
                '--tuples-only', '--no-align', '--field-separator=|',
                '-c', query
            ]
            output = subprocess.check_output(args)
            rows = output.decode('utf-8').splitlines()
            return [row.split('|') for row in rows]

        tables_counters = psql("""\
            SELECT
                tablename,
                CONCAT('SELECT count(*) FROM ', quote_ident(tablename))
            FROM pg_tables WHERE schemaname = 'public';
        """)
        counts = {}
        for table, counter_sql in tables_counters:
            counts[table] = int(psql(counter_sql)[0][0])
        if any(rowcount for table, rowcount in counts.items()):
            message = 'Database has leftover rows!\n{0}'.format(
                ', '.join(
                    '{0}: {1} row(s)'.format(table, rowcount)
                    for table, rowcount in counts.items()
                )
            )
            raise Exception(message)


@pytest.fixture
def app_config(request):
    from pyramid import testing
    from pyramid.paster import get_appsettings

    settings = get_appsettings(TESTS_INI)
    config = testing.setUp(settings=settings)

    request.addfinalizer(testing.tearDown)
    return config


@pytest.fixture
def app_config_models_included(app_config):
    app_config.include('paildocket.models')
    return app_config


@pytest.fixture
def db_session(request, app_config_models_included):
    """
    Reconfigured the registry's SQLAlchemy session and wrap each test
    in a transaction, while still allowing the test to commit and
    rollback at will. Provide the SQLA session to the test function.
    """
    import transaction

    app_config = app_config_models_included
    maker = app_config.registry['db_sessionmaker']
    engine = maker.kw['bind']

    connection = engine.connect()
    # Start a transaction outside of the transaction manager
    outer_transaction = connection.begin()

    # Rebind the connection directly instead of the engine
    maker.configure(bind=connection)

    @request.addfinalizer
    def cleanup():
        # Abort the transaction under the manager, from the test
        transaction.abort()
        # Rollback the outermost transaction and clean up
        outer_transaction.rollback()
        connection.close()

    # Make the session for use in tests
    session_for_test = maker()
    return session_for_test


@pytest.fixture
def testapp(request):
    import transaction
    from pyramid.paster import get_app
    app = get_app(TESTS_INI)

    maker = app.registry['db_sessionmaker']
    engine = maker.kw['bind']

    connection = engine.connect()
    # Start a transaction outside of the transaction manager
    outer_transaction = connection.begin()

    # Rebind the connection directly instead of the engine
    maker.configure(bind=connection)

    @request.addfinalizer
    def cleanup():
        # Abort the transaction under the manager, from the test
        transaction.abort()
        # Rollback the outermost transaction and clean up
        outer_transaction.rollback()
        connection.close()

    from webtest import TestApp
    return TestApp(app)
