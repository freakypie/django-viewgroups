from copy import deepcopy
from django.core.urlresolvers import reverse


class SessionDataMixin(object):
    session_prefix = "data"

    def get_session_prefix(self):
        return "{}:{}".format(self.session_prefix, type(self).__name__)

#     def get_used_parameters(self, *args):
#         return args

    def get_data(self):
        prefix = self.get_session_prefix()
        data = self.request.session.get(prefix, {})
        items = self.request.GET.items()
        if len(items) > 0:
            data = dict(items)
            self.request.session[prefix] = data

        return data