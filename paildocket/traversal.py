from pyramid.decorator import reify
from pyramid.traversal import find_root
from pyramid.security import Allow, Everyone, Authenticated, DENY_ALL

from paildocket.models import Checklist, encoded_userid_to_userid
from paildocket.security import ViewPermission, EditAndViewPermission


class RootResource(object):
    __name__ = None
    __parent__ = None
    __acl__ = [
        (Allow, Everyone, ViewPermission),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        if key == 'user':
            return UsersResource(self)
        elif key == 'list':
            return ChecklistsResource(self)
        else:
            raise KeyError(key)


class ChecklistsResource(object):
    __name__ = 'list'
    __parent__ = None
    __acl__ = [
        (Allow, Authenticated, ViewPermission),
        DENY_ALL
    ]

    def __init__(self, parent):
        self.__parent__ = parent

    def __getitem__(self, key):
        try:
            checklist_id = int(key)
        except ValueError:
            raise KeyError(key)

        return ChecklistResource(self, checklist_id)


class ChecklistResource(object):
    __name__ = None
    __parent__ = None

    def __init__(self, parent, checklist_id):
        self.__parent__ = parent
        self.checklist_id = checklist_id
        self.__name__ = 'checklist.{0}'.format(checklist_id)
        self.request = find_root(self).request

    def __acl__(self):
        acl = []
        user = self.request.user
        if self.checklist is not None and user is not None:
            if user in self.checklist.editors:
                acl.append((Allow, user.principal, EditAndViewPermission))
            elif user in self.checklist.viewers:
                acl.append((Allow, user.principal, ViewPermission))

        acl.append(DENY_ALL)
        return acl

    @reify
    def checklist(self):
        q = self.request.db_session.query(Checklist)
        q = q.filter(Checklist.id == self.checklist_id)
        return q.first()


class UsersResource(object):
    __name__ = 'user'
    __parent__ = None
    __acl__ = [
        (Allow, Authenticated, ViewPermission),
        DENY_ALL
    ]

    def __init__(self, parent):
        self.__parent__ = parent

    def __getitem__(self, key):
        next_ctx = None

        try:
            user_id = encoded_userid_to_userid(key)
        except ValueError:
            raise KeyError(key)

        next_ctx = UserResource(self, user_id)
        return next_ctx


class UserResource(object):
    __name__ = None
    __parent__ = None

    def __init__(self, parent, user_id):
        self.__parent__ = parent
        self.user_id = user_id
        self.__name__ = 'user.{0}'.format(user_id)
        self.request = find_root(self).request

    def __acl__(self):
        acl = []
        user = self.request.user
        if user is not None and self.user_id == user.id:
            acl.append((Allow, user.principal, EditAndViewPermission))

        acl.append(DENY_ALL)
        return acl
