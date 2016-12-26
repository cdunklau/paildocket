class BaseView(object):
    """
    Base view class, just to get rid of the __init__ boilerplate.

    Subclasses should not override __init__. If custom initialization
    needs to be performed, override _extra_init, which will be called
    after the `context` and `request` attributes are set.
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._extra_init()

    def _extra_init(self):
        pass
