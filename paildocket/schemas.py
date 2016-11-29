import string
import re

import colander
import deform.widget

from paildocket.i18n import _


def OnlyCharacters(characters, msg=_('Invalid character(s)')):
    """
    Returns a validator that fails unless the value contains only
    the characters specified, and at least one of them.
    """
    if not characters:
        raise ValueError('Must provide at least one character')
    pattern = r'^[{0}]+$'.format(re.escape(characters))
    return colander.Regex(pattern, msg=msg)


_password_chars = ''.join([
    string.ascii_letters,
    string.digits,
    string.punctuation,
    ' '
])
password_policy = colander.All(
    colander.Length(8, 50),
    OnlyCharacters(_password_chars),
)
username_policy = colander.All(
    colander.Length(3, 30),
    OnlyCharacters(
        string.ascii_letters + string.digits + '-_',
        msg=_('Must only contain letters, numbers, dashes, and/or underscores')
    )
)
email_policy = colander.All(
    colander.Length(max=1000),  # limit "impossible" email addresses
    colander.Email()
)


class LoginSchema(colander.MappingSchema):
    identity = colander.SchemaNode(
        colander.String(),
        title=_('Username or Email Address'),
        # Be forgiving about username/email input for login
        validator=colander.Length(3, 100)
    )
    password = colander.SchemaNode(
        colander.String(),
        title=_('Password'),
        # Be forgiving about password input for login, let the hash do the work
        validator=colander.Length(3, 100),
        widget=deform.widget.PasswordWidget(strip=False)
    )


class RegisterUserSchema(colander.MappingSchema):
    username = colander.SchemaNode(
        colander.String(),
        title=_('Username'),
        validator=username_policy
    )
    email = colander.SchemaNode(
        colander.String(),
        title=_('Email Address'),
        validator=email_policy,
        widget=deform.widget.CheckedInputWidget()
    )
    password = colander.SchemaNode(
        colander.String(),
        title=_('Password'),
        validator=password_policy,
        widget=deform.widget.CheckedPasswordWidget()
    )


class ChecklistSchema(colander.MappingSchema):
    title = colander.SchemaNode(
        colander.String(),
        title=_('Title'),
        validator=colander.Length(0, 500)
    )
    description = colander.SchemaNode(
        colander.String(),
        title=_('Description'),
        validator=colander.Length(0, 10000),
    )
