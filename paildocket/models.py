"""

Glossary:

:encoded_userid:
    The userid encoded with ``base64.urlsafe_b64decode``, with padding
    removed, as a string with length 22.
"""
import logging
from base64 import urlsafe_b64decode, urlsafe_b64encode
from uuid import UUID


from sqlalchemy import (
    Column, UniqueConstraint, CheckConstraint,
    Integer, String, Boolean, ForeignKey,
    or_, and_, not_, text,
    engine_from_config
)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from zope.sqlalchemy import register as zope_sqla_register


logger = logging.getLogger(__name__)


Base = declarative_base()


def userid_to_encoded_userid(userid):
    return urlsafe_b64encode(userid.bytes).decode('ascii').rstrip('=')


def encoded_userid_to_userid(encoded_userid):
    encoded_userid = _repad_base64(encoded_userid)
    return UUID(bytes=urlsafe_b64decode(encoded_userid))


def _repad_base64(trimmed):
    remainder = len(trimmed) % 4
    return trimmed + '=' * (4 - remainder) if remainder else trimmed


class User(Base):
    __tablename__ = 'users'

    id = Column(
        PG_UUID(as_uuid=True), server_default=text('uuid_generate_v4()'),
        primary_key=True
    )
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    admin = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        attrs = ['id', 'username', 'email']
        return '<User({0})>'.format(
            ', '.join('{0}={1!r}'.format(a, getattr(self, a)) for a in attrs))

    @property
    def principal(self):
        return self.email

    @property
    def encoded_userid(self):
        return userid_to_encoded_userid(self.id)

    @classmethod
    def from_request(cls, request):
        logger.debug('Attempting to find request user')
        userid = request.authenticated_userid
        user = None
        if userid is not None:
            logger.debug('Found userid {0!r}'.format(userid))
            q = request.db_session.query(cls).filter(cls.id == userid)
            user = q.one()
        return user

    @classmethod
    def from_encoded_userid(cls, db_session, encoded_userid):
        userid = encoded_userid_to_userid(encoded_userid)
        return cls.from_userid(db_session, userid)

    @classmethod
    def from_userid(cls, db_session, userid):
        return db_session.query(cls).filter(cls.id == userid).first()

    @classmethod
    def from_identity(cls, db_session, identity):
        """
        Return the user identified by ``identity`` or None if the
        user was not found.

        ``identity`` is either the username or the email.
        """
        q = db_session.query(cls)
        q = q.filter(or_(User.username == identity, User.email == identity))
        return q.first()


def _viewer_only_permission_join():
    exp = and_(
        Checklist.id == ChecklistPermission.checklist_id,
        and_(ChecklistPermission.view, not_(ChecklistPermission.edit))
    )
    return exp


def _editor_permission_join():
    exp = and_(
        Checklist.id == ChecklistPermission.checklist_id,
        ChecklistPermission.edit,
    )
    return exp


class Checklist(Base):
    __tablename__ = 'checklists'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False, default='')
    viewer_permissions = relationship(
        'ChecklistPermission',
        primaryjoin=_viewer_only_permission_join,
        collection_class=set,
    )
    editor_permissions = relationship(
        'ChecklistPermission',
        primaryjoin=_editor_permission_join,
        collection_class=set,
    )
    viewers = association_proxy(
        'viewer_permissions', 'user',
        creator=(lambda u: ChecklistPermission.from_viewer_user(u))
    )
    editors = association_proxy(
        'editor_permissions', 'user',
        creator=(lambda u: ChecklistPermission.from_editor_user(u))
    )

    @classmethod
    def editable_by_user_query(cls, db_session, user):
        q = db_session.query(cls)
        q = q.join(*cls.editors.attr)
        q = q.filter(ChecklistPermission.user == user)
        return q

    @classmethod
    def only_viewable_by_user_query(cls, db_session, user):
        q = db_session.query(cls)
        q = q.join(*cls.viewers.attr)
        q = q.filter(ChecklistPermission.user == user)
        return q


class ChecklistItem(Base):
    __tablename__ = 'checklist_items'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False, default='')
    checklist_id = Column(ForeignKey('checklists.id'))


class ChecklistPermission(Base):
    __tablename__ = 'checklists_permissions'
    __table_args__ = (
        # Single permission per checklist/user combination
        UniqueConstraint('checklist_id', 'user_id'),
        # Edit implies view
        CheckConstraint('NOT edit OR view', name='edit_implies_view')
    )

    id = Column(Integer, primary_key=True)
    checklist_id = Column(ForeignKey('checklists.id'), nullable=False)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    user = relationship('User')
    view = Column(Boolean, nullable=False)
    edit = Column(Boolean, nullable=False)

    @classmethod
    def from_viewer_user(cls, viewer_user):
        return cls(user=viewer_user, view=True, edit=False)

    @classmethod
    def from_editor_user(cls, editor_user):
        return cls(user=editor_user, view=True, edit=True)

    @classmethod
    def for_user_and_checklist(cls, db_session, user_id, checklist_id):
        q = db_session.query(cls)
        q = q.filter(cls.user_id == user_id, cls.checklist_id == checklist_id)
        return q.first()


def includeme(config):
    settings = config.get_settings()

    config.include('pyramid_tm')

    engine = engine_from_config(settings, prefix='sqlalchemy.')
    maker = sessionmaker()
    zope_sqla_register(maker)
    maker.configure(bind=engine)
    config.registry['db_sessionmaker'] = maker
    config.add_request_method(
        lambda request: maker(), 'db_session', reify=True)
    config.add_request_method(User.from_request, 'user', reify=True)
