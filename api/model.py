from django.db.models import Field
from django.db.models.fields.related import ForeignKey, ManyToManyField, OneToOneField
from django.db.models.fields.reverse_related import ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel

from lens.utils import logger


# class ModelAPI(APIView):
#     """docstring for ModelAPI"""
#     # def __new__(cls, model_config=None):

#     #     instance = super().__new__(cls)
#     #     instance.model_config = model_config

#     #     #3.返回对象的引用
#     #     return instance

#     def __init__(self, model_config=None):
#         super(ModelAPI, self).__init__()
#         self.model_config = model_config
#         print('self.model_config', self, model_config, self.model_config)

#     def get(self, request, *args, **kwargs):
#         print('get request', self, dir(self), self.request._request, dir(self.request._request), self.model_config, *args, **kwargs)
#         md = self.model_config.get_model_data(request, pagination=True)

#         response = utils.ApiResponse(code=1, data=md.data)
#         print('response.__dict__', md.data, response.__dict__)
#         return JsonResponse(
#             response.__dict__,
#         #     safe=False, # 如果待序列化对象不是dict
#         #     # charset='utf-8',
#             json_dumps_params={'ensure_ascii': False},
#             )

#     def delete(self, request):
#         request.DELETE = QueryDict(request.body)
#         print('data DELETE',
#             # request.body,
#             request.data,
#         request.DELETE, dir(request))
#         action_name = request.DELETE.get('action')
#         action_dict = [{'name': func.__name__, 'text': func.text} for func in self.get_action_list()]
#         print('action_name action_dict', action_name, action_dict)
#         if not action_name:
#             msg = '请求中没有指定批量操作方法'
#         elif action_name not in action_dict:
#             # return HttpResponse('非法请求')
#             msg = '不存在%s方法' % action_name
#         else:
#             # 请求中若有合法action
#             response = getattr(self, action_name)(request)
#             print('data response',response)
#             return JsonResponse(
#                 response.__dict__,
#                 json_dumps_params={'ensure_ascii': False},
#                 )

#         return JsonResponse(
#             utils.ApiResponse(code=-1, msg=msg).__dict__,
#             json_dumps_params={'ensure_ascii': False},
#             )

#     def post(self, request):
#         AddModelForm = self.get_model_form_class()
#         form = AddModelForm(request.POST)
#         print('form', form.errors.as_json(), type(form.errors.as_json()))
#         code = -1

#         if form.is_valid():
#             form.save()
#             code = 1

#         data = json.loads(form.errors.as_json())
#         response = utils.ApiResponse(code, data=data)
#         return JsonResponse(
#             response.__dict__,
#             json_dumps_params={'ensure_ascii': False},
#             )


class ModelData(object):
    """非前后端分离模式下 model的数据序列化类
    """

    def __init__(self, config, queryset, q, search_list, page=None, count=None, pagination=True):
        '''
        Arguments:
            config {[ModelConfig]} -- [model的配置类]
            queryset {[type]} -- [description]
            q {[type]} -- [description]
            search_list {[type]} -- [description]

        Keyword Arguments:
            page {[type]} -- [description] (default: {None})
            count {[type]} -- [description] (default: {None})
            pagination {bool} -- [是否分页 若否 某些值就无须构建] (default: {True})
        '''
        # logger.info('ModelData __init__',
        #     config
        # )

        self.q = q
        self.search_list = search_list
        self.page = page
        self.count = count
        self.pagination = pagination

        self.config = config
        # self.action_list = [{'name': func.__name__, 'text': func.text} for func in config.get_action_list()]

        # if self.pagination:
        #     self.add_btn = config.get_add_btn()

        self.queryset = queryset
        self.list_filter = config.get_list_filter()

    # def gen_list_filter_rows(self):

    #     for option in self.list_filter:
    #         _field = self.config.model_class._meta.get_field(option.field)
    #         yield option.get_queryset(_field, self.config.model_class, self.config.request.GET)

    def get_rel_value(self, query, field):
        ''' 对model中的Rel字段进行取值

        [description]

        Arguments:
            filed {[string]} -- [field名称]

        Returns:
            [type] -- [description]
        '''
        # logger.info('get_rel_value',
        #     type(field),
        #     field,
        #     field.name,
        #     field.__dict__,
        #     queryset,
        #     queryset.__dict__
        #     type(query),
        #     query.__dict__,
        #     query.values_list(),
        #     )

        # 处理fk/m2m字段
        if isinstance(field, OneToOneRel):
            # logger.info('> OneToOneRel',
            #     field.name,
            #     queryset.values_list('pk', flat=True),
            #     )
            queryset = getattr(query, field.name)
            # 根据配置类的depth决定是否进行反向关联字段的序列化
            if not self.config.depth:
                val = queryset.pk
            elif self.config.depth == 1:
                val = model_to_dict(
                    queryset, fields=[field.name for field in queryset._meta.fields])
        elif isinstance(field, (ManyToOneRel, ManyToManyRel)):
            # logger.info('> ManyToOneRel, ManyToManyRel',
            #     )
            queryset = getattr(query, field.name + '_set').all()
            # 根据配置类的depth决定是否进行反向关联字段的序列化
            if not self.config.depth:
                val = [i.pk for i in queryset]
            elif self.config.depth == 1:
                val = list(queryset.values())

        # logger.info('> val',
        #     field.name,
        #     val,
        #     )
        return val

    def get_field_value(self, query, field):
        ''' 对model中的字段进行取值

        [description]

        Arguments:
            filed {[string]} -- [field名称]

        Returns:
            [type] -- [description]
        '''
        queryset = getattr(query, field.name)
        # logger.info('get_field_value',
        #     type(field),
        #     field,
        #     field.name,
        #     )

        # 处理fk、o2o/m2m字段(OneToOneField走的也是ForeignKey)
        if isinstance(field, ForeignKey):
            # logger.info('> ForeignKey',
            #     field,
            #     type(queryset),
            #     )
            if not queryset:
                val = None
            elif not self.config.depth:
                val = queryset.pk or queryset.__str__()
            elif self.config.depth == 1:
                # val = model_to_dict(queryset)
                val = model_to_dict(
                    queryset, fields=[field.name for field in queryset._meta.fields])
        elif isinstance(field, (ManyToManyField,)):
            # logger.info('> ManyToManyField',
            #     field.name,
            #     queryset.values_list('pk', flat=True),
            #     )
            queryset = getattr(query, field.name).all()
            if not self.config.depth:
                val = [i.pk for i in queryset]
            elif self.config.depth == 1:
                val = list(queryset.values())
        # 处理常规field
        else:
            # logger.info('> else',)
            val = queryset
        # logger.info('> val',
        #     field.name, val,
        #     )
        return val

    def get_item(self, query):
        ''' 获取一行的数据
        Arguments:
            query {[type]} -- [description]

        Returns:
            [type] -- [description]
        '''
        item = {}
        # logger.info('field_class_list',
        #             self.config.field_class_list
                    # )
        for field in self.config.field_class_list:
            # logger.info('get_item for', type(field), field)
            if isinstance(field, (Field)):
                # 若为Model的常规字段 则进行取值
                # 若为ModelConfig.display_checkbox等非model字段 则跳过
                try:
                    val = self.get_field_value(query, field)
                except Exception as e:
                    # print('except:',e)
                    val = '无法处理的字段:%s, 错误:%s' % (field, str(e))
            elif isinstance(field, (ForeignObjectRel)):
                try:
                    val = self.get_rel_value(query, field)
                except Exception as e:
                    # print('except:',e)
                    val = '无法处理的Rel字段:%s, 错误:%s' % (field, str(e))
            else:
                continue
            item[field.name] = val
        for field in self.config.property_show_list:
            val = getattr(query, field)
            # logger.info('get_item property_show_list', type(field), field, val)

            item[field] = val
        return item

    def get_items(self):
        ''' 获取queryset中所有行的数据
        '''
        return [self.get_item(query) for query in self.queryset]

    @property
    def data(self):
        ''' 为API构造数据 对fk/m2m字段单独进行了处理
        '''
        _meta = self.config.model_class._meta

        rows = {
            'app': {
                'name': _meta.app_label,
                'label': _meta.app_config.verbose_name,
            },
            'name': _meta.model_name,
            'table': _meta.model_name,
            'label': _meta.verbose_name,
            # 'fields': {
            #     _meta.get_field(k).name: (_meta.get_field(k).related_model._meta.verbose_name if isinstance(
            #         _meta.get_field(k), (ManyToManyRel, ManyToOneRel)) else _meta.get_field(k).verbose_name)
            #     for k in self.list_display
            #     if isinstance(k, str)
            # },
            'items': self.get_items()
        }
        # logger.info('rows',
        #     rows,
        #     type(rows),
        #     dir(rows)
        #     )
        # yield row
        return rows
