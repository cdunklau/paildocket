import logging

import deform
import colander
from pyramid.view import view_config, view_defaults
from pyramid.httpexceptions import HTTPFound

from paildocket.views import BaseView
from paildocket.i18n import _
from paildocket.models import User
from paildocket.security import ViewPermission
from paildocket.traversal import UserCollectionResource, UserResource


logger = logging.getLogger(__name__)


@view_defaults(context=UserCollectionResource, permission=ViewPermission)
class UserCollectionViews(BaseView):
    """
    Display and management of the currently logged-on user.
    """
    @view_config(renderer='user/display.jinja2')
    def index(self):
        return {'user': self.request.user}


@view_defaults(context=UserResource, permission=ViewPermission)
class UserViews(BaseView):
    @view_config(renderer='json')
    def index(self):
        return {'user_id': str(self.context.user_id)}
