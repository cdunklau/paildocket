import pytest

from paildocket.tests.support import parametrize_with_ids


def assert_validator_validates(validator, value):
    from colander import Invalid
    try:
        validator(None, value)
    except Invalid:
        msg = 'Failed to validate {value!r}'
        pytest.fail(msg.format(value=value))


def assert_validator_fails_to_validate(validator, value):
    from colander import Invalid
    with pytest.raises(Invalid):
        validator(None, value)


@parametrize_with_ids(
    'chars,value', [
        ('a', 'a', 'single character'),
        ('a', 'aaa', 'single character, multiple values'),
        ('!@#', '!!@@##', 'special characters validate'),
    ]
)
def test_onlycharacters_validates(chars, value):
    from paildocket.schemas import OnlyCharacters
    validator = OnlyCharacters(chars)
    assert_validator_validates(validator, value)


@parametrize_with_ids(
    'chars,value', [
        ('a', '', 'empty value is invalid'),
        ('a', 'ab', 'invalid although value includes acceptable'),
        ('a-c', 'b', 'special characters get escaped'),
        ('!@#', 'abc', 'special characters invalid'),
    ]
)
def test_onlycharacters_validation_fails(chars, value):
    from paildocket.schemas import OnlyCharacters
    validator = OnlyCharacters(chars)
    assert_validator_fails_to_validate(validator, value)


def test_onlycharacters_requires_at_least_one_char():
    from paildocket.schemas import OnlyCharacters
    with pytest.raises(ValueError):
        OnlyCharacters('')


@parametrize_with_ids(
    'password', [
        ('12345678', 'minimum length 8'),
        ('a' * 50, 'maximum length 50'),
        ('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~', 'punctuation allowed'),
        (' ' * 8, 'spaces allowed'),
    ]
)
def test_password_policy_validates(password):
    from paildocket.schemas import password_policy
    assert_validator_validates(password_policy, password)


@parametrize_with_ids(
    'password', [
        ('', 'empty is invalid'),
        ('1234567', 'too short'),
        ('a' * 51, 'too long'),
        ('\N{PILE OF POO}' * 8, 'non-ascii not allowed'),
        ('\t' * 8, 'special whitespace not allowed'),
        ('\0' * 8, 'nonprintable not allowed'),
    ]
)
def test_password_policy_validation_fails(password):
    from paildocket.schemas import password_policy
    assert_validator_fails_to_validate(password_policy, password)


@parametrize_with_ids(
    'username', [
        ('aaa', 'minimum length 3'),
        ('a' * 30, 'maximum length 30'),
        ('abcDEF123-_', 'letters, numbers, dashes, or underscores allowed'),
    ]
)
def test_username_policy_validates(username):
    from paildocket.schemas import username_policy
    assert_validator_validates(username_policy, username)


@parametrize_with_ids(
    'username', [
        ('aa', 'too short'),
        ('a' * 31, 'too long'),
        ('   ', 'spaces disallowed'),
        ('\t\t\t', 'other whitespace disallowed'),
        ('!!!', 'punctuation disallowed'),
    ]
)
def test_username_policy_validation_fails(username):
    from paildocket.schemas import username_policy
    assert_validator_fails_to_validate(username_policy, username)


@parametrize_with_ids(
    'email', [
        ('t@f.co', 'tiny email still works'),
        ('foo.bar@example.com', 'normal email works'),
        ('a' * 995 + '@f.co', 'max email size works'),
    ]
)
def test_email_policy_validates(email):
    from paildocket.schemas import email_policy
    assert_validator_validates(email_policy, email)


@parametrize_with_ids(
    'email', [
        ('sfd@', 'invalid email fails'),
        ('a' * 996 + '@f.co', 'huge email fails'),
    ]
)
def test_email_policy_validation_fails(email):
    from paildocket.schemas import email_policy
    assert_validator_fails_to_validate(email_policy, email)


def assert_schema_deserializes_to_same(schema, cstruct):
    from colander import Invalid
    try:
        appstruct = schema.deserialize(cstruct)
    except Invalid as error:
        msg = (
            'Expected good cstruct {cstruct!r} failed deserialization by'
            'schema {schema!r}, exception {error!r}'
        )
        pytest.fail(msg.format(cstruct=cstruct, schema=schema, error=error))
    else:
        assert appstruct == cstruct


def assert_schema_deserialize_fails(schema, cstruct):
    from colander import Invalid
    with pytest.raises(Invalid) as excinfo:
        schema.deserialize(cstruct)
    return excinfo


@parametrize_with_ids(
    'identity,password', [
        ('123', 'abc', 'minimum length 3'),
        ('a' * 100, 'p' * 100, 'maximum length 100')
    ]
)
def test_loginschema_validates(identity, password):
    from paildocket.schemas import LoginSchema
    schema = LoginSchema()
    cstruct = {'identity': identity, 'password': password}
    assert_schema_deserializes_to_same(schema, cstruct)


@parametrize_with_ids(
    'identity,password,problem_node', [
        ('12', 'abc', 'identity', 'identity too short'),
        ('a' * 101, 'abc', 'identity', 'identity too long'),
        ('123', 'ab', 'password', 'password too short'),
        ('abc', 'a' * 101, 'password', 'password too long'),
    ]
)
def test_loginschema_validation_fails_on_node_name(
        identity, password, problem_node):
    from paildocket.schemas import LoginSchema
    schema = LoginSchema()
    cstruct = {'identity': identity, 'password': password}
    excinfo = assert_schema_deserialize_fails(schema, cstruct)
    errorfields = excinfo.value.asdict()
    assert errorfields.keys() == set([problem_node])


# TODO more tests
@parametrize_with_ids(
    'username,email,password', [
        ('min', 'm@f.cc', '12345678', 'bare minimum lengths'),
    ]
)
def test_registerschema_validates(username, email, password):
    from paildocket.schemas import RegisterUserSchema
    schema = RegisterUserSchema()
    cstruct = {'username': username, 'email': email, 'password': password}
    assert_schema_deserializes_to_same(schema, cstruct)


# TODO add tests for invalid RegisterSchema cstructs
