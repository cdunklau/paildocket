from paildocket.config import make_config


def main(global_config, **settings):
    return make_config(global_config, **settings).make_wsgi_app()
