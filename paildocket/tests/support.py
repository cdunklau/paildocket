import os.path
import uuid

import pytest

from paildocket.security import create_password_context


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_INI = os.path.join(TESTS_DIR, 'unittests.ini')


UUID_USERID = uuid.UUID('ccd6a2d7-a22a-4487-97a4-9afef9d77718')
ENCODED_USERID = 'zNai16IqRIeXpJr--dd3GA'

insecure_but_fast_password_context = create_password_context(
    bcrypt__default_rounds=4)
insecure_hash_password = insecure_but_fast_password_context.encrypt


class DummyObject(object):
    pass


class DummyCallable(object):
    def __init__(self, returnval):
        self.args = None
        self.kwargs = None
        self.returnval = returnval

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self.returnval

    @property
    def called(self):
        return self.args is not None and self.kwargs is not None


def parametrize_with_ids(argspec, testdata_with_doc):
    """
    Like `pytest.mark.parametrize`, but interprets the last element
    of each tuple in ``testdata_with_doc`` as the test id.

    This implies that the number of args in ``argspec`` is one fewer
    than the length of each tuple in ``testdata_with_doc``
    """
    testdata = []
    idlist = []
    for tup in testdata_with_doc:
        *args, id = tup
        if len(args) == 1:
            args = args[0]  # because the parametrize API is inconsistant
        testdata.append(args)
        idlist.append(id)
    return pytest.mark.parametrize(argspec, testdata, ids=idlist)
