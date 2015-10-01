import logging

import deform
import colander
from pyramid.view import view_config, view_defaults
from pyramid.httpexceptions import HTTPFound

from paildocket.i18n import _
from paildocket.models import Checklist
from paildocket.security import ViewPermission
from paildocket.traversal import ChecklistsResource, ChecklistResource


logger = logging.getLogger(__name__)


@view_defaults(context=ChecklistsResource, permission=ViewPermission)
class ChecklistsViews(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(renderer='checklist/index.jinja2')
    def index(self):
        db_session = self.request.db_session
        user = self.request.user
        editable = Checklist.editable_by_user_query(db_session, user)
        viewable = Checklist.only_viewable_by_user_query(db_session, user)
        return {
            'editable': editable.all(),
            'viewable': viewable.all(),
        }


@view_defaults(context=ChecklistResource, permission=ViewPermission)
class ChecklistView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(renderer='json')
    def index(self):
        return {'checklist_id': self.context.checklist_id}
