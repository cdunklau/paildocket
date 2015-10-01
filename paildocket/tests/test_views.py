from urllib.parse import urlparse

import pytest
from pyramid.testing import DummyRequest, DummyResource
from paildocket.tests.support import DummyObject, ENCODED_USERID


def create_user_in_testapp(testapp):
    db_session = testapp.app.registry['db_sessionmaker']()
    password_hasher = testapp.app.registry['password_context'].encrypt
    create_user_from_db_session(db_session, password_hasher)


def create_user_from_db_session(db_session, password_hasher=None):
    import transaction
    from paildocket.models import User
    if password_hasher is None:
        from paildocket.tests.support import (
            insecure_hash_password as password_hasher
        )
    user = User(
        username='testuser',
        email='testuser@example.com',
        password_hash=password_hasher('testuserpass'),
    )
    db_session.add(user)
    db_session.flush()
    transaction.commit()


def create_test_view_instance(view_class, context=None, request=None):
    context = DummyResource() if context is None else context
    request = DummyRequest() if request is None else request
    return view_class(context, request)


def test_forbidden_view_with_user_returns_403():
    from paildocket.views.root import forbidden
    request = DummyRequest()
    request.user = True
    response = forbidden(request)
    assert response.status_int == 403


def test_forbidden_view_without_user_returns_redirect_to_login():
    from paildocket.views.root import forbidden
    request = DummyRequest()
    request.user = False
    request.context = DummyResource()
    response = forbidden(request)
    assert urlparse(response.location).path == '/login'


def test_root_view():
    from paildocket.views.root import RootViews

    inst = create_test_view_instance(RootViews)
    info = inst.index()
    assert info['project'] == 'paildocket'


class TestLoginView(object):
    def _make_inst(self):
        from paildocket.views.root import LoginView
        request = DummyRequest()
        request.registry['password_context'] = DummyObject()
        return create_test_view_instance(LoginView, request=request)

    def test_display_returns_form(self):
        inst = self._make_inst()
        result = inst.display()
        assert result['form'] is inst.form


#
# Functional tests for views
#
@pytest.mark.functional
def test_test_app(testapp):
    res = testapp.get('/', status=200)
    assert b'This project is called paildocket' in res.body


@pytest.mark.functional
@pytest.mark.parametrize(
    'path', [
        '/user', '/user/{0}'.format(ENCODED_USERID),
        '/list', '/list/123', '/list/123/',
    ]
)
def test_protected_resource_redirects_to_login(testapp, path):
    res = testapp.get(path, status=302)
    assert urlparse(res.location).path == '/login'


@pytest.mark.functional
@pytest.mark.parametrize(
    'username,identity,password', [
        ('testuser', 'testuser', 'testuserpass'),
        ('testuser', 'testuser@example.com', 'testuserpass'),
    ]
)
def test_login_with_username_or_email(testapp, username, identity, password):
    create_user_in_testapp(testapp)
    res = _login(testapp, identity, password)
    # should redirect to root resource
    assert urlparse(res.headers['location']).path == '/'

    res = res.follow()
    logged_in_greeting = b''.join([b'Hello, ', username.encode('utf-8'), b'!'])
    assert logged_in_greeting in res.body

    res = testapp.get('/user', status=200)
    assert username.encode('utf-8') + b"&#39;s profile" in res.body


@pytest.mark.functional
@pytest.mark.parametrize(
    'identity,password', [
        ('otheruser', 'testuserpass'),  # wrong username
        ('otheruser@example.com', 'testuserpass'),  # wrong email
        ('testuser', 'wrongpass'),  # wrong password
        ('testuser@example.com', 'wrongpass'),  # wrong password
    ]
)
def test_login_failed(testapp, identity, password):
    create_user_in_testapp(testapp)
    res = _login(testapp, identity, password, status=200)
    assert b'Unknown username/email or incorrect password' in res.body


def _login(testapp, identity, password, **kwargs):
    res = testapp.get('/login', status=200)
    form = res.forms['login_form']
    form['identity'] = identity
    form['password'] = password
    res = form.submit('submit', **kwargs)
    return res


@pytest.mark.functional
def test_user_registration(testapp):
    from paildocket.models import User

    res = testapp.get('/register', status=200)
    form = res.forms['register_form']
    form['username'] = 'foobar'
    form['email'] = 'foobar@example.com'
    form['email-confirm'] = 'foobar@example.com'
    form['password'] = 'foobarfoobar'
    form['password-confirm'] = 'foobarfoobar'
    res = form.submit('submit')

    # should redirect to login form
    assert urlparse(res.headers['location']).path == '/login'

    password_context = testapp.app.registry['password_context']
    db_session = testapp.app.registry['db_sessionmaker']()
    user = db_session.query(User).first()
    assert user.username == 'foobar'
    assert user.email == 'foobar@example.com'
    assert password_context.verify('foobarfoobar', user.password_hash)
