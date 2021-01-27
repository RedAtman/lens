from django.apps import apps
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS


class ApiResponse(object):
    """docstring for Response"""
    _status = {
        -1: '失败',
        0: '未知错误',
        1: '成功',
    }

    def __init__(self, code=0, msg=None, msg_list=[], data={}):
        # super(Response, self).__init__()
        if not self._status.get(code):
            self._status[code] = msg
        self.code = code
        # self.status_code = code
        # self.msg = self.init_msg()
        if msg_list:
            html = ['<ul class="list-group">', '</ul>']
            for x in msg_list:
                html.insert(-1, '<div class="alert alert-danger" role="alert">' +
                            str(x) + '</div>')
            self.msg = ''.join(html)
        else:
            self.msg = msg or self._status.get(code)
        self.data = data
