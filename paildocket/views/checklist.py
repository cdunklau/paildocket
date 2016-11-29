import logging

import deform
from pyramid.view import view_config, view_defaults
from pyramid.httpexceptions import HTTPFound

from paildocket.i18n import _
from paildocket.models import Checklist
from paildocket.schemas import ChecklistSchema
from paildocket.security import ViewPermission
from paildocket.traversal import ChecklistCollectionResource, ChecklistResource


logger = logging.getLogger(__name__)


@view_defaults(context=ChecklistCollectionResource, permission=ViewPermission)
class ChecklistCollectionViews(object):
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


@view_defaults(context=ChecklistCollectionResource, permission=ViewPermission)
class ChecklistCreateViews(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = deform.Form(
            ChecklistSchema(),
            action=request.resource_url(context, request.view_name),
            buttons=(deform.Button('submit', title=_('Create')),),
            formid='checklist_form',
        )

    @view_config(name='create', request_method='GET',
                 renderer='checklist/create.jinja2')
    def display(self):
        return {'form': self.form}

    @view_config(name='create', request_method='POST',
                 renderer='checklist/create.jinja2')
    def process(self):
        try:
            checklist = self.validate()
        except deform.ValidationFailure as error_form:
            return {'form': error_form}
        self.request.db_session.add(checklist)
        self.request.db_session.flush()
        destination = self.request.resource_url(self.context[checklist.id])
        return HTTPFound(location=destination)

    def validate(self):
        data = self.form.validate(self.request.POST.items())
        checklist = Checklist(
            title=data['title'],
            description=data['description'],
        )
        checklist.editors.add(self.request.user)
        return checklist


@view_defaults(context=ChecklistResource, permission=ViewPermission)
class ChecklistView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(renderer='json')
    def index(self):
        checklist = self.context.checklist
        return {
            'id': checklist.id,
            'title': checklist.title,
            'description': checklist.description,
        }
