import deform

from pkg_resources import resource_filename
from pyramid.i18n import TranslationStringFactory, get_localizer
from pyramid.threadlocal import get_current_request


_ = PaildocketTranslationString = TranslationStringFactory('paildocket')


class AcceptLanguageLocaleNegotiator(object):
    """
    A Pyramid locale negotiator that inspects the request's
    Accept-Language header, and provides the best match to
    the browser's preference based on the application's
    declared ``available_languages``, and optionally falls back
    to another negotiator if the match fails.
    """
    def __init__(self, available_languages, fallback=None):
        self._available_languages = available_languages
        self._fallback = (lambda r: None) if fallback is None else fallback

    def __call__(self, request):
        if request.accept_language:
            return request.accept_language.best_match(
                self._available_languages)
        else:
            # no or empty Accept-Language, fall back to next negotiator
            return self._fallback(request)


class SessionLocaleNegotiator(object):
    """
    A Pyramid locale negotiator that inspects the session for a 'lang'
    key, otherwise uses the ``fallback_negotiator`` to try to figure
    it out, and if found sets it in the session.
    """
    def __init__(self, fallback_negotiator):
        self.fallback_negotiator = fallback_negotiator

    def __call__(self, request):
        language = request.session.get('lang')
        if language is None:
            language = self.fallback_negotiator(request)
            if language is not None:
                request.session['lang'] = language
        return language


def includeme(config):
    config.registry.setdefault('default_locale_name', 'en')
    config.add_translation_dirs(
        'paildocket:locale',
        'colander:locale',
        'deform:locale',
    )

    available = ['en', 'de']
    locale_negotiator = SessionLocaleNegotiator(
        AcceptLanguageLocaleNegotiator(available))
    config.set_locale_negotiator(locale_negotiator)

    def translator(term):
        return get_localizer(get_current_request()).translate(term)

    deform_template_dir = resource_filename('deform', 'templates/')
    zpt_renderer = deform.ZPTRendererFactory(
        [deform_template_dir], translator=translator)
    deform.Form.set_default_renderer(zpt_renderer)
