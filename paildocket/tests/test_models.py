import pytest

from paildocket.tests.support import ENCODED_USERID, UUID_USERID, DummyObject


ALICE = 'alice'
ALICE_HASH = 'alicehash'
ALICE_EMAIL = 'alice@example.com'


class TestUserModel(object):
    def test_principal(self):
        from paildocket.models import User

        user = User(email=ALICE_EMAIL)
        assert user.principal == ALICE_EMAIL

    def test_creation(self, db_session):
        from paildocket.models import User

        new_user = User(
            username='dummy',
            password_hash='dummyhash',
            email='dummy@example.com',
        )
        db_session.add(new_user)
        q = db_session.query(User).filter_by(username='dummy')
        retrieved_user = q.first()
        assert new_user == retrieved_user
        assert retrieved_user.id is not None

    def test_unique_username(self, db_session):
        from sqlalchemy.exc import IntegrityError
        from paildocket.models import User

        alice1 = User(
            username=ALICE,
            email='alice1@example.com',
            password_hash=ALICE_HASH
        )
        db_session.add(alice1)
        db_session.flush()

        alice2 = User(
            username=ALICE,
            email='alice2@example.com',
            password_hash=ALICE_HASH
        )
        db_session.add(alice2)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_users_unique_email(self, db_session):
        from sqlalchemy.exc import IntegrityError
        from paildocket.models import User

        alice1 = User(
            username='alice1',
            password_hash=ALICE_HASH,
            email=ALICE_EMAIL
        )
        db_session.add(alice1)
        db_session.flush()

        alice2 = User(
            username='alice2',
            password_hash=ALICE_HASH,
            email=ALICE_EMAIL
        )
        db_session.add(alice2)
        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_from_request(self, db_session):
        from paildocket.models import User

        alice = User(
            username=ALICE,
            password_hash=ALICE_HASH,
            email=ALICE_EMAIL,
        )
        db_session.add(alice)
        db_session.flush()

        fake_request = DummyObject()
        fake_request.db_session = db_session
        fake_request.authenticated_userid = alice.id

        returned = User.from_request(fake_request)
        assert returned is alice

    def test_from_request_returns_none_if_authuser_is_none(self):
        from paildocket.models import User

        fake_request = DummyObject()
        fake_request.authenticated_userid = None

        returned = User.from_request(fake_request)
        assert returned is None

    def test_from_identity(self, db_session):
        from paildocket.models import User

        alice = User(
            username=ALICE, password_hash=ALICE_HASH, email=ALICE_EMAIL)
        db_session.add(alice)
        db_session.flush()

        by_username = User.from_identity(db_session, ALICE)
        assert alice is by_username
        by_email = User.from_identity(db_session, ALICE_EMAIL)
        assert alice is by_email


@pytest.mark.parametrize(
    'input,expected',
    [
        ('', ''),
        ('a', 'a==='),
        ('ab', 'ab=='),
        ('abc', 'abc='),
        ('abcd', 'abcd'),
        ('abcda', 'abcda==='),
        ('abcdab', 'abcdab=='),
        ('abcdabc', 'abcdabc='),
        ('abcdabcd', 'abcdabcd'),
        ('abcdabcda', 'abcdabcda==='),
    ]
)
def test__repad_base64(input, expected):
    from paildocket.models import _repad_base64

    assert _repad_base64(input) == expected


def test_encoded_userid_to_userid_no_padding():
    from paildocket.models import encoded_userid_to_userid
    assert encoded_userid_to_userid(ENCODED_USERID) == UUID_USERID


def test_userid_to_encoded_userid():
    from paildocket.models import userid_to_encoded_userid
    result = userid_to_encoded_userid(UUID_USERID)
    assert result == ENCODED_USERID
    assert type(result) is str


def test_invalid_encoded_userid_raises_valueerror():
    from paildocket.models import encoded_userid_to_userid
    with pytest.raises(ValueError):
        encoded_userid_to_userid('1')
