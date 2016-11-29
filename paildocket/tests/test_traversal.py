import pytest

from paildocket.traversal import (
    RootResource, UserCollectionResource, UserResource,
    ChecklistCollectionResource, ChecklistResource
)
from paildocket.tests.support import ENCODED_USERID, UUID_USERID


class FakeRequest(object):
    pass


def root_resource_factory():
    return RootResource(FakeRequest())


def checklists_resource_factory():
    return ChecklistCollectionResource(root_resource_factory())


def users_resource_factory():
    return UserCollectionResource(root_resource_factory())


@pytest.mark.parametrize(
    'resource_factory,key,classinfo', [
        (root_resource_factory, 'user', UserCollectionResource),
        (root_resource_factory, 'list', ChecklistCollectionResource),
        (checklists_resource_factory, '123', ChecklistResource),
        (users_resource_factory, ENCODED_USERID, UserResource),
    ]
)
def test_resource_getitem_returns_instance_with_parent(resource_factory, key,
                                                       classinfo):
    """
    Ensure that the resource obtained by calling ``resource_factory``
    will provide an instance of ``classinfo`` based on the ``key``.
    """
    resource = resource_factory()
    child = resource[key]
    assert isinstance(child, classinfo)
    assert child.__parent__ is resource


@pytest.mark.parametrize(
    'resource_factory,key', [
        (root_resource_factory, 'bogus'),
        # root views
        (root_resource_factory, ''),
        (root_resource_factory, 'login'),
        (root_resource_factory, 'logout'),
        (root_resource_factory, 'register'),
        (checklists_resource_factory, 'not_an_integer_string'),
        (users_resource_factory, 'unconvertable_to_uuid'),
    ]
)
def test_resource_getitem_raises_keyerror(resource_factory, key):
    resource = resource_factory()
    with pytest.raises(KeyError):
        resource[key]


def test_checklists_resource_int_key_child():
    checklists_resource = checklists_resource_factory()
    assert checklists_resource['123'].checklist_id == 123


def test_users_resource_userid_child():
    users_resource = users_resource_factory()
    assert users_resource[ENCODED_USERID].user_id == UUID_USERID


# Integration tests
@pytest.mark.parametrize(
    'path,resource_type,view_name', [
        (['user'], UserCollectionResource, ''),
        (['user', 'login'], UserCollectionResource, 'login'),
        (['user', 'logout'], UserCollectionResource, 'logout'),
        (['user', 'register'], UserCollectionResource, 'register'),
        (['list'], ChecklistCollectionResource, ''),
        (['list', '123'], ChecklistResource, ''),
    ]
)
def test_traversal__path_type_view_name(path, resource_type, view_name):
    """
    Ensure that traversing the ``path`` results in a resource of type
    ``resource_type`` with view name ``view_name``.
    """
    from pyramid.traversal import traverse
    root_resource = root_resource_factory()
    t = traverse(root_resource, path)
    assert isinstance(t['context'], resource_type)
    assert t['view_name'] == view_name


@pytest.mark.parametrize(
    'path,attribute_name,value', [
        (['user', ENCODED_USERID], 'user_id', UUID_USERID),
        (['list', '123'], 'checklist_id', 123),
    ]
)
def test_traversal__path_resource_attribute(path, attribute_name, value):
    """
    Ensure that traversing the ``path`` results in a resource having
    the attribute ``attribute_name`` set to ``value``.

    """
    from pyramid.traversal import traverse
    root_resource = root_resource_factory()
    t = traverse(root_resource, path)
    context = t['context']
    assert getattr(context, attribute_name) == value
