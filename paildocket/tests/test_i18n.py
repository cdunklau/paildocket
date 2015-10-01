def pytest_generate_tests(metafunc):
    if 'module_for_i18n_test' in metafunc.fixturenames:
        modules = list(generate_paildocket_modules())
        metafunc.parametrize('module_for_i18n_test', modules)


def generate_paildocket_modules():
    from os.path import dirname
    from pkgutil import walk_packages
    from importlib import import_module

    import paildocket

    paildocket_dir = dirname(paildocket.__file__)
    walker = walk_packages([paildocket_dir], prefix='paildocket.')
    for ign, module_fqn, ign in walker:
        yield import_module(module_fqn)


def test_module_uses_i18n_translation_string(module_for_i18n_test):
    """
    Ensure that the name ``_`` refers to
    ``paildocket.i18n.PaildocketTranslationString`` in the module
    if the module defines that name.
    """
    from paildocket.i18n import PaildocketTranslationString

    try:
        _ = getattr(module_for_i18n_test, '_')
    except AttributeError:
        pass
    else:
        assert _ is PaildocketTranslationString


class TestAcceptLanguageLocaleNegotiator(object):
    def make_negotiator(self, available_languages, fallback=None):
        from paildocket.i18n import AcceptLanguageLocaleNegotiator
        return AcceptLanguageLocaleNegotiator(
            available_languages, fallback=fallback)

    def make_request_accepting_language(self, accept_language=None):
        from pyramid.request import Request
        request = Request({})
        if accept_language is not None:
            request.accept_language = accept_language
        return request

    def test_no_languages_returns_none(self):
        negotiator = self.make_negotiator([])
        request = self.make_request_accepting_language()
        assert negotiator(request) is None

    def test_no_languages_calls_fallback_with_request(self):
        from paildocket.tests.support import DummyCallable
        fallback = DummyCallable('fallback called')
        negotiator = self.make_negotiator([], fallback=fallback)
        request = self.make_request_accepting_language()
        assert negotiator(request) == 'fallback called'
        assert fallback.args[0] is request

    def test_no_language_for_none_available(self):
        negotiator = self.make_negotiator([])
        request = self.make_request_accepting_language('en')
        assert negotiator(request) is None

    def test_no_language_for_unsupported(self):
        negotiator = self.make_negotiator(['en'])
        request = self.make_request_accepting_language('pt')
        assert negotiator(request) is None

    def test_supported_language(self):
        negotiator = self.make_negotiator(['en'])
        request = self.make_request_accepting_language('en')
        assert negotiator(request) == 'en'

    def test_browser_first_choice_used_if_supported(self):
        negotiator = self.make_negotiator(['en', 'de'])
        request = self.make_request_accepting_language('de;q=0.9, en;q=0.8')
        assert negotiator(request) == 'de'

    def test_browser_second_choice_used_if_first_unsupported(self):
        negotiator = self.make_negotiator(['en'])
        request = self.make_request_accepting_language('de;q=0.9, en;q=0.8')
        assert negotiator(request) == 'en'

    def test_preferred_language_but_with_locale_is_still_selected(self):
        negotiator = self.make_negotiator(['en', 'de'])
        request = self.make_request_accepting_language('de-DE;q=0.9, en;q=0.8')
        assert negotiator(request) == 'de'


class TestSessionLocaleNegotiator(object):
    def make_request(self, session_language=None):
        from pyramid.testing import DummyRequest
        request = DummyRequest()
        request.session = {}
        if session_language is not None:
            request.session['lang'] = session_language
        return request

    def make_negotiator(self, fallback_value=None):
        from paildocket.i18n import SessionLocaleNegotiator
        from paildocket.tests.support import DummyCallable
        fallback = DummyCallable(fallback_value)
        return SessionLocaleNegotiator(fallback)

    def test_session_preference_used(self):
        negotiator = self.make_negotiator()
        request = self.make_request(session_language='en')
        assert negotiator(request) == 'en'

    def test_session_falls_back(self):
        negotiator = self.make_negotiator(fallback_value='value')
        request = self.make_request(session_language=None)
        assert negotiator(request) == 'value'
        assert negotiator.fallback_negotiator.called
        assert negotiator.fallback_negotiator.args[0] is request

    def test_session_falls_back_setting_value_in_session(self):
        negotiator = self.make_negotiator(fallback_value='value')
        request = self.make_request(session_language=None)
        negotiator(request)
        assert request.session['lang'] == 'value'

    def test_session_falls_back_no_session_if_fallback_returns_none(self):
        negotiator = self.make_negotiator(fallback_value=None)
        request = self.make_request(session_language=None)
        assert negotiator(request) is None
        assert request.session == {}
