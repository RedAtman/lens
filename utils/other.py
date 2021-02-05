import collections


class ApiResponse(object):
    '''lensAPI响应

    Variables:
        _status {dict} -- [description]
        } {[type]} -- [description]
    '''
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


class OrderedSet(collections.Set):
    '''保持顺序的set
    '''

    def __init__(self, iterable=()):
        self.d = collections.OrderedDict.fromkeys(iterable)

    def __len__(self):
        return len(self.d)

    def __contains__(self, element):
        return element in self.d

    def __iter__(self):
        return iter(self.d)
