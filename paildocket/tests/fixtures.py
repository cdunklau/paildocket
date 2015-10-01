# This is broken, needs reimplementation
"""
Routines for loading and adding fixture data.


"""
import os.path
import glob
import itertools
import logging
import functools
import json

from paildocket.models import (
    User, Checklist, ChecklistItem, ChecklistPermission
)
from paildocket.tests.support import insecure_hash_password, TESTS_DIR


logger = logging.getLogger(__name__)


TESTFILES_DIR = os.path.join(TESTS_DIR, 'files')


class FixtureIntegrityError(Exception):
    pass


class Fixture(object):
    def __init__(self):
        self._users_map = {}
        self._checklists = []

    @classmethod
    def from_dict(cls, structure):
        """
        Create a fixture and populate it with data from a primative
        structure (e.g. loaded from a json file).
        """
        inst = cls()
        user_dicts = structure.pop('users')
        checklist_dicts = structure.pop('checklists')
        if structure:
            raise FixtureIntegrityError(
                "Unexpected key(s) in root of structure: {0}".format(
                    _format_keys(structure)))
        for user_dict in user_dicts:
            inst.load_user(UserFixtureModel.from_dict(user_dict))
        for checklist_dict in checklist_dicts:
            inst.load_checklist(
                ChecklistFixtureModel.from_dict(checklist_dict,
                                                inst._users_map))
        return inst

    @classmethod
    def from_fixture_models(cls, users, checklists):
        inst = cls()
        for user in users:
            inst.load_user(user)
        for checklist in checklists:
            inst.load_checklist(checklist)
        return inst

    def to_dict(self):
        return {
            'users': [user.to_dict() for user in self._users_map.values()],
            'checklists': [
                checklist.to_dict() for checklist in self._checklists]
        }

    def load_user(self, user):
        if user.username in self._users_map:
            raise FixtureIntegrityError(
                "Username {0} already exists!".format(user.username))
        self._users_map[user.username] = user

    def load_checklist(self, checklist):
        self._checklists.append(checklist)

    def insert_all(self):
        for user in self._users_map.values():
            user.insert()
        for checklist in self._checklists:
            checklist.insert()


class BaseFixtureModel(object):
    def __init__(self):
        self._id = None

    @property
    def id(self):
        if self._id is None:
            raise FixtureIntegrityError(
                'Tried to get ID before it is available')
        return self._id


class UserFixtureModel(BaseFixtureModel):
    def __init__(self, *, username, password=None, email=None):
        super().__init__()
        self.username = username
        self.password = password or username
        self.email = email or '{0}@example.com'.format(
            username.replace(' ', '.'))

    @classmethod
    def from_dict(cls, user_dict):
        username = user_dict.pop('username')
        password = user_dict.pop('password', None)
        email = user_dict.pop('email', None)
        if user_dict:
            raise FixtureIntegrityError(
                "Unexpected key(s) for user {0!r}: {1}".format(
                    username, _format_keys(user_dict)))
        return cls(username=username, password=password, email=email)

    def to_dict(self):
        return {
            'username': self.username, 'password': self.password,
            'email': self.email
        }

    def insert(self):
        password_hash = insecure_hash_password(self.password)
        self._id = db.user_repository.insert(
            username=self.username,
            email=self.email,
            password_hash=password_hash
        )


class ChecklistFixtureModel(BaseFixtureModel):
    def __init__(self, *, title, description,
                 editors=(), viewers=(), items=()):
        super().__init__()
        self.title = title
        self.description = description
        self.items = items
        self.editors = editors
        self.viewers = viewers
        self._id = None

    @classmethod
    def from_dict(cls, checklist_dict, users_map):
        title = checklist_dict.pop('title')
        description = checklist_dict.pop('description')
        item_dicts = checklist_dict.pop('items')
        editor_names = checklist_dict.pop('editor_usernames', ())
        viewer_names = checklist_dict.pop('viewer_usernames', ())

        items = []
        for item_dict in item_dicts:
            items.append(ItemFixtureModel.from_dict(item_dict))
        editors = [users_map[username] for username in editor_names]
        viewers = [users_map[username] for username in viewer_names]

        if checklist_dict:
            raise FixtureIntegrityError(
                "Unexpected key(s) for checklist {0!r}: {1}".format(
                    title, _format_keys(checklist_dict)))

        return cls(title=title, description=description, items=items,
                   editors=editors, viewers=viewers)

    def to_dict(self):
        return {
            'title': self.title, 'description': self.description,
            'items': [item.to_dict() for item in self.items],
            'editor_usernames': [user.username for user in self.editors],
            'viewer_usernames': [user.username for user in self.viewers],
        }

    def insert(self):
        checklist_id = db.checklist_repository.insert(
            title=self.title, description=self.description)
        for viewer in self.viewers:
            db.checklists_permission_repository.insert_or_update(
                checklist_id=checklist_id, user_id=viewer.id, view=True)
        for editor in self.editors:
            db.checklists_permission_repository.insert_or_update(
                checklist_id=checklist_id, user_id=editor.id, edit=True)
        self._id = checklist_id
        for item in self.items:
            item.insert(checklist=self)


class ItemFixtureModel(BaseFixtureModel):
    def __init__(self, *, title, description):
        super().__init__()
        self.checklist = None
        self.title = title
        self.description = description

    @classmethod
    def from_dict(cls, item_dict):
        title = item_dict.pop('title')
        description = item_dict.pop('description')
        if item_dict:
            raise FixtureIntegrityError(
                "Unexpected key(s) for item {0!r}: {1}".format(
                    title, _format_keys(item_dict)))

        return cls(title=title, description=description)

    def to_dict(self):
        return {'title': self.title, 'description': self.description}

    def insert(self, *, checklist):
        self.checklist = checklist
        self._id = db.item_repository.insert(
            checklist_id=self.checklist.id,
            title=self.title,
            description=self.description
        )


def _format_keys(d):
    return ', '.join(repr(k) for k in d)


installable_fixtures = set(
    os.path.basename(path).rpartition('.')[0] for path
    in glob.glob(os.path.join(TESTFILES_DIR, '*.json')))
generatable_fixtures = {}


def get_fixture_path(fixture_name):
    return os.path.join(TESTFILES_DIR, fixture_name + '.json')


def install_fixture(fixture_name):
    fixture_path = get_fixture_path(fixture_name)
    logger.info('Loading fixture {0!r} from file {1!r}'.format(
        fixture_name, fixture_path))
    with open(fixture_path, 'r') as f:
        structure = json.load(f)
    fixture = Fixture.from_dict(structure)
    logger.info('Installing into database')
    fixture.insert_all()


def regenerate_fixture(fixture_name, *, indent=False):
    logger.info('Regenerating fixture {0!r}'.format(fixture_name))
    fixture_generator = generatable_fixtures[fixture_name]
    structure = fixture_generator().to_dict()
    path = get_fixture_path(fixture_name)
    logger.info('Writing fixture data to {0!r}'.format(path))
    with open(path, 'w') as f:
        # sort_keys to keep the output consistant regardless of hash seed
        json.dump(structure, f, sort_keys=True, indent=indent)


def fixture_generator(fixture_name):
    """
    Decorator to register fixture generators.

    A fixture generator is a callable with no arguments which returns
    a ``Fixture`` instance populated with fixture model instances.

    :param fixture_name:    The fixture filename consists of the
                            ``fixture_name`` with a json extension
                            added.
    """
    if type(fixture_name) is not str:
        raise TypeError('fixture_name must be a string')
    def decorator(func):
        if fixture_name in generatable_fixtures:
            msg = 'fixture with name {0} already registered'.format(
                fixture_name)
            raise FixtureIntegrityError(msg)
        if fixture_name == 'all':
            raise FixtureIntegrityError('Cannot use special value "all"')
        generatable_fixtures[fixture_name] = func
        return func
    return decorator


@fixture_generator('minimal')
def minimal_fixture():
    alice = UserFixtureModel(username='alice')
    checklist = ChecklistFixtureModel(
        title="Alice's checklist",
        description="",
        items=[ItemFixtureModel(title="Alice's item", description="")],
        editors=[alice]
    )
    return Fixture.from_fixture_models(users=[alice], checklists=[checklist])


def multiple_items(nitems, lipsum):
    items = []
    for _ in range(nitems):
        item = ItemFixtureModel(
            title=next(lipsum),
            description=lipsum.paragraphs()
        )
        items.append(item)
    return items


@fixture_generator('large_text_sample')
def large_text_sample():
    lipsum = LipsumGenerator()

    alice, bob, charles = [
        UserFixtureModel(username=name) for name
        in ('alice', 'bob', 'charles')
    ]

    alice_private_checklist = ChecklistFixtureModel(
        title="Alice's private checklist",
        description=lipsum.paragraphs(),
        items=multiple_items(10, lipsum),
        editors=(alice,))

    alice_semipublic_checklist = ChecklistFixtureModel(
        title="Alice's shared checklist",
        description=lipsum.paragraphs(),
        items=multiple_items(10, lipsum),
        editors=(alice,),
        viewers=(bob, charles))

    bob_private_checklist = ChecklistFixtureModel(
        title="Bob's private checklist",
        description=lipsum.paragraphs(),
        items=multiple_items(10, lipsum),
        editors=(bob,))

    return Fixture.from_fixture_models(
        users=[alice, bob, charles],
        checklists=[
            alice_private_checklist,
            alice_semipublic_checklist,
            bob_private_checklist
        ]
    )


@fixture_generator('realistic_data')
def realistic_data():
    alice, bob, charles = [
        UserFixtureModel(username=name) for name
        in ('alice', 'bob', 'charles')
    ]
    users = [alice, bob, charles]
    checklists = [
        ChecklistFixtureModel(
            title="Alice's private checklist",
            description="Alice likes to keep her bucket list here",
            editors=[alice],
            items=[
                ItemFixtureModel(
                    title="Go skydiving",
                    description="I've always been afraid of heights, time "
                                "to stop caring about that."
                )
            ]
        ),
        ChecklistFixtureModel(
            title="Bob's private list - books to read",
            description="Bob keeps track of the books he wants to read",
            editors=[bob],
            items=[
                ItemFixtureModel(
                    title="Gödel, Escher, Bach",
                    description="by Douglas Hofstadter"
                )
            ]
        ),
        ChecklistFixtureModel(
            title="Alice's shared movie recommendations",
            description="Alice suggests movies to Charles and Bob",
            editors=[alice],
            viewers=[bob, charles],
            items=[
                ItemFixtureModel(
                    title="Back to the Future",
                    description="I can't believe you guys haven't seen this"
                )
            ]
        )
    ]
    return Fixture.from_fixture_models(users=users, checklists=checklists)


LIPSUM_SENTENCES = [
    line.rstrip() for line in
    open(os.path.join(TESTFILES_DIR, 'lipsum.txt'), encoding='utf-8')]


def lipsum_paragraph(n, offset=0):
    """
    Return a string containing a paragraph of `n` sentences of
    lorem ipsum text, offset from the source list by `offset`.
    """
    indices = range(offset, n + offset)
    return ' '.join(LIPSUM_SENTENCES[i] for i in indices)


def lipsum_sentences():
    """
    Infinite generator of lorem ipsum sentences.
    """
    return itertools.cycle(LIPSUM_SENTENCES)


class LipsumGenerator(object):
    def __init__(self):
        self._iter = lipsum_sentences()

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)

    def paragraph(self, nsentences=8):
        return ' '.join(itertools.islice(self, nsentences))

    def paragraphs(self, nparagraphs=3, nsentences=8):
        return '\n\n'.join(
            self.paragraph(nsentences) for _ in range(nparagraphs))
