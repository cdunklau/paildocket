import logging

import deform
import colander
from pyramid.view import view_config, view_defaults, forbidden_view_config
from pyramid.security import remember, forget
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.traversal import find_root
from sqlalchemy import or_

from paildocket.i18n import _
from paildocket.models import User
from paildocket.schemas import LoginSchema, RegisterUserSchema
from paildocket.traversal import RootResource


logger = logging.getLogger(__name__)


@forbidden_view_config()
def forbidden(request):
    if request.user:
        # User exists, but tried to access something they don't have
        # permission for.
        return HTTPForbidden('You are not allowed to perform this action')
    else:
        # No user is logged in, so redirect to login form
        destination = request.resource_url(find_root(request.context), 'login')
        return HTTPFound(location=destination)


@view_defaults(context=RootResource)
class RootViews(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(renderer='index.jinja2')
    def index(self):
        return {'project': 'paildocket'}

    @view_config(name='test', renderer='test.jinja2')
    def test(self):
        user = self.request.user
        accept_language_value = self.request.accept_language
        values = [accept_language_value, user]
        return {
            'value_repr_types': [(v, repr(v), repr(type(v))) for v in values],
        }

    @view_config(name='logout')
    def logout(self):
        headers = forget(self.request)
        destination = self.request.resource_url(self.context)
        return HTTPFound(location=destination, headers=headers)


@view_defaults(name='login', renderer='login.jinja2', context=RootResource)
class LoginView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = deform.Form(
            LoginSchema(),
            action=request.resource_url(context, request.view_name),
            buttons=(deform.Button('submit', title=_('Log In')),),
            formid='login_form',
        )
        self.password_context = request.registry['password_context']

    @view_config(request_method='GET')
    def display(self):
        return {'form': self.form}

    @view_config(request_method='POST')
    def process(self):
        try:
            user = self.validate()
        except deform.ValidationFailure as error_form:
            return {'form': error_form}
        destination = self.request.resource_url(self.context)
        headers = self.log_user_on(user)
        return HTTPFound(location=destination, headers=headers)

    def validate(self):
        """
        Return the user object, or raise `deform.ValidationFailure`
        if the form validation fails or the identity and password
        do not match a user.
        """
        data = self.form.validate(self.request.POST.items())
        identity = data['identity']
        password = data['password']
        user = User.from_identity(self.request.db_session, identity)
        if user is None:
            # Eliminate timing differences for unknown identity case
            # versus invalid password.
            self.password_context.encrypt(password)
        else:
            if self.verify_password_possible_update(password, user):
                return user
        message = _('Unknown username/email or incorrect password')
        self.form.error = colander.Invalid(None, message)
        raise deform.ValidationFailure(self.form, self.form.cstruct, None)

    def verify_password_possible_update(self, password, user):
        """
        Verify the password against the user's password hash, and
        upgrade the hash if necessary. Return true if the password
        was verified successfully.
        """
        verify_and_update = self.password_context.verify_and_update
        valid, new_hash = verify_and_update(password, user.password_hash)
        if valid and new_hash:
            logger.info('Upgrading password hash for user {0!r}'.format(user))
            user.password_hash = new_hash
            self.request.db_session.add(user)
            self.request.db_session.flush()
        return valid

    def log_user_on(self, user):
        """
        Create and save an auth ticket and return the headers needed
        to set the auth cookie.
        """
        principal = user.email
        headers = remember(self.request, principal)
        return headers


@view_defaults(
    name='register',
    renderer='register.jinja2',
    context=RootResource,
)
class RegisterView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        schema = RegisterUserSchema()
        self.form = deform.Form(
            schema,
            action=request.resource_url(self.context, 'register'),
            buttons=(deform.Button('submit', title=_('Register')),),
            formid='register_form'
        )

    @view_config(request_method='GET')
    def display(self):
        return {'form': self.form}

    @view_config(request_method='POST')
    def process(self):
        try:
            username, email, password = self.validate()
        except deform.ValidationFailure as error_form:
            return {'form': error_form}
        self.register_user(username, email, password)
        destination = self.request.resource_url(self.context, 'login')
        return HTTPFound(location=destination)

    def validate(self):
        """
        Return the username, email, and password, or raise
        `deform.ValidationFailure` if the form validation fails, or
        if the username or email already exists.
        """
        data = self.form.validate(self.request.POST.items())
        username = data['username']
        email = data['email']
        password = data['password']
        if self.check_already_registered(username, email):
            message = _('The username or email address is already registered')
            # Set message as an error for the whole form
            self.form.error = colander.Invalid(None, message)
            raise deform.ValidationFailure(self.form, self.form.cstruct, None)

        return username, email, password

    def check_already_registered(self, username, email):
        q = self.request.db_session.query(User)
        q = q.filter(or_(User.username == username, User.email == email))
        return self.request.db_session.query(q.exists()).scalar()

    def register_user(self, username, email, password):
        password_context = self.request.registry['password_context']
        password_hash = password_context.encrypt(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        self.request.db_session.add(user)
