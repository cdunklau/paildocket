import pytest

from paildocket.tests.support import ENCODED_USERID, UUID_USERID


class TestAuthenticationPolicy(object):
    def make_policy(self, *args, **kwargs):
        from paildocket.security import PaildocketAuthenticationPolicy
        if not args and 'secret' not in kwargs:
            args = ('thisisasecret',)
        return PaildocketAuthenticationPolicy(*args, **kwargs)

    def make_request(self, db_session):
        from pyramid.request import Request
        request = Request({})
        request.db_session = db_session
        return request

    @pytest.skip('not done yet')
    def test_remember_creates_new_ticket(self, db_session):
        policy = self._make_policy()
        request = self.make_request(db_session)
        headers = policy.remember(something)
