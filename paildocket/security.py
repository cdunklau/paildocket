"""

Glossary:

:userid:
    The User model instance's ID (a ``uuid.UUID`` instance).
:principal:
    In the context of a user's principal, the user's email.

"""
import datetime
import hashlib
import logging
from os import urandom

from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import Everyone, Authenticated
from pyramid.settings import asbool
from passlib.context import CryptContext
from webob.cookies import SignedCookieProfile
from zope.interface import implementer

from paildocket.models import User, UserTicket


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


_iso_format = '%Y-%m-%dT%H:%M:%S'


@implementer(IAuthenticationPolicy)
class PaildocketAuthenticationPolicy(object):
    def __init__(self, secret, salt='paildocket-auth', cookie_name='auth',
                 secure=False, http_only=False, path='/', domains=None,
                 hashalg='sha512', timeout=None, reissue_time=None,
                 max_age=None, debug=False):
        """
        :param secret:
            Secret for the secure cookie generator.
        :param salt:
            Salt for collision protection (but don't use the same
            secret anyway).
        :param cookie_name:
            Name of the auth ticket cookie.
        :param secure:
            Only send the cookie over a secure connection.
        :param http_only:
            Set HttpOnly flag on the cookie to prevent access by
            JavaScript (on conforming browsers).
        :param path:
            The path for the cookie.
        :param domains:
            The domains for the cookie.
        :param hashalg:
            The hashing algorithm to use for the cookie signature.
        :param timeout:
            The maximum age of the ticket, in seconds. When this amount
            of time passes after the ticket is created, the ticket will
            no longer be valid.
        :param reissue_time:
            The number of seconds before an authentication token cookie
            is reissued. If provided, must be less than `timeout`.
        :param max_age:
            The maximum age of the cookie in the browser, in seconds.
            If provided, must be greater than `timeout` and
            `reissue_time`.
        :param debug:
            If true, log verbosely.
        """
        if secure:
            raise NotImplementedError
        if reissue_time:
            if not timeout or reissue_time >= timeout:
                raise ValueError('reissue_time must be less than timeout')
        if max_age:
            if not timeout or timeout >= max_age:
                raise ValueError('max_age must be greater than timeout')
            if not reissue_time or reissue_time >= max_age:
                raise ValueError('max_age must be greater than reissue_time')

        self.cookie = SignedCookieProfile(
            secret, salt, cookie_name,
            secure=secure,
            httponly=http_only,
            path=path,
            domains=domains,
            hashalg=hashalg,
            max_age=max_age,
        )
        self.reissue_time = reissue_time
        self.timeout = timeout
        self.debug = debug

    def _new_ticket(self):
        randbytes = 32
        hashalg = 'sha256'
        return hashlib.new(hashalg, urandom(randbytes)).hexdigest()

    def remember(self, request, principal, **kwargs):
        if self.debug:
            logger.debug(
                '`remember` called with principal {0!r}'.format(principal))
        value = {}
        value['principal'] = principal
        value['ticket'] = ticket = self._new_ticket()
        value['issued'] = datetime.datetime.utcnow().strftime(_iso_format)

        q = request.db_session.query(User).filter(User.email == principal)
        user = q.first()

        if user is None:
            raise ValueError('Unknown principal {0!r}'.format(principal))

        remote_address = request.environ.get('REMOTE_ADDR')
        user.tickets.append(
            UserTicket(ticket=ticket, remote_address=remote_address))

        return self.cookie.get_headers(value)

    def forget(self, request):
        if self.debug:
            logger.debug('`forget` called')
        ticket_instance = request.auth.get('ticket_instance')
        if ticket_instance:
            request.db_session.delete(ticket_instance)
        request.auth['revoked'] = True
        return self.cookie.get_headers('', max_age=0)

    def unauthenticated_userid(self, request):
        """No support for unauthenticated userid"""
        if self.debug:
            logger.debug('`unauthenticated_userid` called')
        return None

    def authenticated_userid(self, request):
        # TODO: break this up, it's way too complex
        if self.debug:
            logger.debug('`authenticated_userid` called')

        userid = request.auth.get('userid')
        if userid is not None:
            if self.debug:
                fmt = 'Found userid {0!r} already in request.auth'
                logger.debug(fmt.format(userid))
            return userid

        result = self.cookie.bind(request).get_value()

        if not result:
            if self.debug:
                logger.debug('Failed to find auth ticket in cookie')
            return None

        principal = result['principal']
        ticket = result['ticket']
        issued_unparsed = result['issued']
        issued = datetime.datetime.strptime(issued_unparsed, _iso_format)

        if self.debug:
            fmt = (
                'Cookie contains ticket {0!r} for principal {1!r} issued {2!r}'
            )
            logger.debug(fmt.format(ticket, principal, issued_unparsed))

        ticket_instance = UserTicket.find_ticket_with_principal(
            request.db_session, ticket, principal)

        if ticket_instance is None:
            fmt = (
                'Failed to locate ticket {0!r} for principal {1!r} in database'
            )
            logger.debug(fmt.format(ticket, principal))
            return None

        userid = ticket_instance.user_id

        # TODO fix this, authenticated_userid must return None if timed out
        self._timeout_or_reissue(request, ticket_instance, issued, principal)

        request.auth['userid'] = userid
        request.auth['ticket_instance'] = ticket_instance

        return userid

    def effective_principals(self, request):
        principals = [Everyone]
        userid = self.authenticated_userid(request)

        if userid is None:
            return principals

        if request.user.admin:
            principals.append(Administrator)

        principals.append(Authenticated)
        principals.append(request.user.principal)

        return principals

    def _timeout_or_reissue(self, request, ticket_instance, issued, principal):
        now = datetime.datetime.utcnow()
        headers = self._get_timeout_headers(request, now, ticket_instance)
        if not headers:
            headers = self._get_reissue_headers(
                request, now, ticket_instance, issued, principal)

        if headers:
            def add_reissue_or_revoke_headers(request, response):
                auth = request.auth
                if 'reissued' not in auth and 'revoked' not in auth:
                    for k, v in headers:
                        response.headerlist.append((k, v))
            request.add_response_callback(add_reissue_or_revoke_headers)

    def _get_timeout_headers(self, request, now, ticket_instance):
        if self.timeout:
            elapsed = (now - ticket_instance.created)
            if elapsed.total_seconds() > self.timeout:
                return self.forget(request)

    def _get_reissue_headers(self, request, now, ticket_instance, issued,
                             principal):
        if self.reissue_time and 'reissued' not in request.auth:
            elapsed = (now - issued)
            if elapsed.total_seconds() > self.reissue_time:
                request.db_session.delete(ticket_instance)
                request.auth['reissued'] = True
                return self.remember(request, principal)


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
    config.add_request_method(lambda request: {}, name='auth', reify=True)

    _authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(_authz_policy)
