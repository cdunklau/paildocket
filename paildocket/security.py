"""

Glossary:

:userid:
    The User model instance's ID (a ``uuid.UUID`` instance).
:principal:
    In the context of a user's principal, the user's email.

"""
import logging

from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.security import Authenticated
from pyramid.settings import asbool
from passlib.context import CryptContext

from paildocket.models import User


logger = logging.getLogger(__name__)


PASSWORD_CONTEXT_DEFAULT_POLICY = {
    'schemes': ('bcrypt',),
    'default': 'bcrypt',
    'bcrypt__default_rounds': 12,
}


def create_password_context(**replacement_kwargs):
    for key, value in list(replacement_kwargs.items()):
        if value is None:
            del replacement_kwargs[key]
    kwargs = PASSWORD_CONTEXT_DEFAULT_POLICY.copy()
    kwargs.update(replacement_kwargs)
    return CryptContext(**kwargs)


Administrator = 'paildocket.Administrator'
ViewPermission = 'paildocket.permission.View'
EditPermission = 'paildocket.permission.Edit'
EditAndViewPermission = (ViewPermission, EditPermission)


def _get_principals(userid, request):
    user = User.from_userid(request.db_session, userid)
    if user is None:
        return None
    principals = [Authenticated]
    if user.admin:
        principals.append(Administrator)
    principals.append(user.principal)
    return principals


MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR


def includeme(config):
    bcrypt_rounds = config.registry.settings.get(
        'paildocket.password.bcrypt_rounds')
    config.registry['password_context'] = create_password_context(
        bcrypt__default_rounds=bcrypt_rounds
    )

    _auth_debug = asbool(
        config.registry.settings.get('paildocket.authentication.debug', False))
    _authn_policy = AuthTktAuthenticationPolicy(
        secret=config.registry.settings['paildocket.authentication.secret'],
        callback=_get_principals,
        timeout=14 * DAY,
        reissue_time=1 * DAY,
        max_age=30 * DAY,
        debug=_auth_debug
    )
    config.set_authentication_policy(_authn_policy)

    _authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(_authz_policy)
