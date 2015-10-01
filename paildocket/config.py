from pyramid.config import Configurator
from pyramid_jinja2.filters import (
    route_url_filter, static_url_filter, model_url_filter
)

from paildocket.traversal import RootResource


def make_config(global_config, **settings):
    settings.update({
        'jinja2.filters': {
            'route_url': route_url_filter,
            'static_url': static_url_filter,
            'resource_url': model_url_filter,
        },
        'jinja2.extensions': ['jinja2.ext.i18n'],
    })

    config = Configurator(settings=settings, root_factory=RootResource)

    config.include('pyramid_jinja2')
    config.add_jinja2_search_path('paildocket:templates/')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('deform_static', 'deform:static/')

    config.include('paildocket.i18n')
    config.include('paildocket.models')
    config.include('paildocket.session')
    config.include('paildocket.security')

    config.scan('paildocket.views')
    return config
