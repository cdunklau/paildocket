from pyramid.session import SignedCookieSessionFactory
from webob.cookies import JSONSerializer


def includeme(config):
    _session_factory = SignedCookieSessionFactory(
        config.registry.settings['paildocket.session.secret'],
        httponly=False,  # ensure AJAX can send session
        max_age=864000,
        timeout=864000,
        reissue_time=1200,
        serializer=JSONSerializer(),
    )

    config.set_session_factory(_session_factory)
