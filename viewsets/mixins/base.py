from copy import deepcopy
from django.urls import reverse


class SessionDataMixin(object):
    session_prefix = "data"

    def get_session_prefix(self):
        return "{}:{}".format(self.session_prefix, type(self).__name__)

#     def get_used_parameters(self, *args):
#         return args

    def get_data(self):
        prefix = self.get_session_prefix()

        data = getattr(self, "___stored_data", None)
        if data is None:
            data = self.request.session.get(prefix, {})
            items = self.request.GET.copy()
            items.pop("page", 1)

            # clear
            cleared = False
            for key in ("_clear", "_"):
                if key in items:
                    data = {}
                    cleared = True
                    items.pop(key, None)
                    break

            # remove specific keys
            if "_remove" in items:
                for remove in items.get("_remove", "").split(","):
                    if remove in data:
                        del data[remove]
                        cleared = True
                items.pop("_remove", None)

            if len(items.keys()) > 0 or cleared:
                for n, v in items.items():
                    data[n] = v
                self.request.session[prefix] = data

            self.___stored_data = data

        return data.copy()
