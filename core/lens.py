import functools
import json
import re
# from types import FunctionType
import traceback

from django.conf.urls import url
# from django.utils.safestring import mark_safe
# from django.shortcuts import HttpResponse, render, redirect
from django.http import QueryDict, JsonResponse
from django.http.request import HttpRequest
# from django.http import FileResponse
# from django.urls import reverse
from django import forms
from django.db.models import Q, Avg, Max, Min, Count, Field
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel
from django.db.models.query_utils import DeferredAttribute
from django.core import serializers
from django.forms.models import model_to_dict

from lens import lens_settings, utils, api, schema
from lens.utils import logger, decorator
from lens.settings import perform_import


# 生产环境请将settings中的DEBUG设置为False 部分不安全的接口与测试功能将关闭
from django.conf import settings


# 根据DEBUG切换开发/生产环境下被允许的请求方法
if settings.DEBUG:
    ACCEPT_REQUEST_METHOD = [
        'GET', 'POST', 
        'PATCH', 'DELETE'
    ]
else:
    ACCEPT_REQUEST_METHOD = ['GET', 'POST', 'PATCH', ]

# 允许的聚合查询
ACCEPT_AGGREGATE = {
    # 'avg': Avg, 
    'max': Max, 
    'min': Min, 
    # 'count': Count
}


class ModelConfig(object):

    def multi_delete(self, request):
        """
        批量删除的action
        :param request:
        :return:
        """

        pk_list = request.data.get('pk_list', [])
        if len(pk_list) == 0:
            return JsonResponse(
                utils.ApiResponse(-1, '未选择任何项 指定参数(action)后 参数(pk_list)不能为空', {}).__dict__,
                json_dumps_params={'ensure_ascii': False},
            )
        if isinstance(pk_list, list):
            result = self.model_class.objects.filter(pk__in=pk_list).delete()
        else:
            result = self.model_class.objects.get(pk=pk_list).delete()
        # logger.info('multi_delete result', pk_list, result)
        data = {'result': list(result)}
        if result[0] == 0:
            code = -1
            msg = '数据库中无pk为%s的数据' % str(pk_list)
        else:
            code = 1
            msg = 'success'
        return JsonResponse(
            utils.ApiResponse(code, msg, data).__dict__,
            json_dumps_params={'ensure_ascii': False},
            )

    multi_delete.text = "批量删除"

    versioning_class = lens_settings.DEFAULT_VERSIONING_CLASS
    # 指定以某些字段排序
    order_by = []
    # 允许显示的字段
    field_show_list = []
    # 禁止显示的字段
    field_hide_list = []
    # 允许以field身份显示的属性
    property_show_list = []
    # 模糊搜索的字段范围
    field_search_list = []
    action_list = [multi_delete]
    list_filter = []
    model_form_class = None
    is_pagination = True
    depth = 0

    def __init__(self, model_class, site):
        self.model_class = model_class
        self.site = site
        self.request = None
        self.back_condition_key = "_filter"
        self.page = 1
        self.per_page = 100
        self._initialize()

    def _initialize(self):
        self._classify_fields()
        self._build_field_class_list()
        self._build_field_name_list()
        # print('field_show_list', self.field_show_list)
        # print('property_show_list', self.property_show_list)
        # print('field_class_list', self.field_class_list)

    def _classify_fields(self):
        '''分拣field与property
        '''
        # 若未定义则默认显示所有field和property
        if not self.field_show_list:
            field_list = [i.name for i in self.model_class._meta.get_fields()]
            property_list = [i for i in dir(self.model_class) if isinstance(getattr(self.model_class, i), decorator.Property)]
            self.field_show_list = field_list + property_list
        # print('self.field_show_list', self.field_show_list)

        # 差集: 剔除配置中禁止显示的field 并使用utils.OrderedSet保持set差集的顺序
        field_show_list = list(utils.OrderedSet(self.field_show_list) - utils.OrderedSet(self.field_hide_list))
        # print('field_show_list', field_show_list)

        # 分拣field与property
        self.field_show_list = []
        self.property_show_list = []
        for field in field_show_list:
            if hasattr(self.model_class, field): # 这里避开了外键类型的字段 有优化空间
                f = getattr(self.model_class, field)
                if isinstance(f, DeferredAttribute):
                    self.field_show_list.append(field)
                elif isinstance(f, decorator.Property):
                    self.property_show_list.append(field)

    def _build_field_class_list(self):
        '''生成model的字段类列表
        '''
        self.field_class_list = [field for field in self.model_class._meta.get_fields() if field.name in self.field_show_list]

    def _build_field_name_list(self):
        ''' 获取model的字段类名列表
        '''
        self.field_name_list = [field.name for field in self.field_class_list]

    def get_order_by(self):
        return self.order_by

    def get_field_show_list(self):
        # val.extend([ModelConfig.display_checkbox,ModelConfig.display_edit,ModelConfig.display_del,ModelConfig.display_index,])
        val = []
        val.extend(self.field_show_list)
        return val

    def get_action_list(self):
        val = []
        val.extend(self.action_list)
        return val

    def get_field_search_list(self):
        val = []
        if self.field_search_list:
            val.extend(self.field_search_list)
        else:
            val.extend(self.field_name_list)
        return val

    def get_search_condition(self, request, pk=None):
        con = Q()
        field_search_list = self.get_field_search_list()  # ['name','tel']
        q = request.GET.get('q', "")
        if q:
            # 生成模糊搜索条件
            con.connector = "OR"
            for field in field_search_list:
                # print('field',type(field),field)
                _field = self.model_class._meta.get_field(field)
                if isinstance(_field, (ManyToManyField, ManyToManyRel)):
                    # print('_field',type(field),field)
                    continue
                elif isinstance(_field, (ForeignKey, ManyToOneRel)):
                    # continue
                    # print('_field',
                    #     field,
                        # type(_field),
                        # _field, 
                        # _field.target_field,
                        # dir(_field.target_field),
                        # _field.target_field.name,
                        # )
                    con.children.append(('%s__%s__contains' % (field, _field.target_field.name), q))
                else:
                    con.children.append(('%s__contains' % field, q))
        else:
            # 生成字段精确搜索条件
            con.connector = "AND"

            # 筛选出查询key 与 当前model的非外键fields的交集
            query_fields = set(request.data.keys())
            # print('5'*20, query_fields)
            query_fields = query_fields & {local_field.name for local_field in self.model_class._meta.local_fields}

            for field in query_fields:
                con.children.append(('%s' % field, request.data.get(field, "")))
            # print('query_fields', query_fields, field_search_list, q, con)

        return field_search_list, q, con

    def get_list_filter(self):
        val = []
        val.extend(self.list_filter)
        return val

    def get_list_filter_condition(self):
        comb_condition = {}
        for option in self.get_list_filter():
            element = self.request.GET.getlist(option.field)
            if element:
                comb_condition['%s__in' % option.field] = element

        return comb_condition


    def get_model_data(self, request, pk=None, pagination=True):
        '''[summary]
        
        [description]
        
        Arguments:
            request {[type]} -- [description]
        
        Keyword Arguments:
            pagination {bool} -- [是否分页] (default: {True})
        
        Returns:
            [type] -- [description]
        '''

        # ##### 处理搜索 #####
        field_search_list, q, con = self.get_search_condition(request, pk=pk)

        # 获取组合搜索筛选
        condition = self.get_list_filter_condition()
        # print('field_search_list, q, con', field_search_list, q, con, condition)

        # 生成Max、Min聚合查询条件并返回查询数据
        for key in ACCEPT_AGGREGATE.keys():
            # print('key, func', key)
            field = request.GET.get(key, '')
            if field:
                ret = self.model_class.objects.all().aggregate(value=ACCEPT_AGGREGATE.get(key)(field))
                # print('aggregate', ret, field)
                queryset = self.model_class.objects.filter(**{field:ret.get('value')})
                md = api.ModelData(self, queryset, q, field_search_list, pagination=pagination)
                return md

        # pagination若为False 则不处理分页及count
        if not pagination:
            queryset = self.model_class.objects.filter(con).filter(**condition).order_by(*self.get_order_by()).distinct()

            md = api.ModelData(self, queryset, q, field_search_list, pagination=pagination)
        else:
            # ##### 处理分页 #####
            # print('con',type(con),con)
            total_count = self.model_class.objects.filter(con).count()
            query_params = request.GET.copy()
            query_params._mutable = True

            try:
                self.page = int(request.GET.get('page'))
            except Exception as e:
                self.page = 1

            page = utils.Pagination(self.page, total_count, request.path_info, query_params, per_page=self.per_page)

            # 获取组合搜索筛选
            queryset = self.model_class.objects.filter(con).filter(**condition).order_by(*self.get_order_by()).distinct()[page.start:page.end]

            # 获取count
            count = self.model_class.objects.count()

            md = api.ModelData(self, queryset, q, field_search_list, page, count, pagination=pagination)

        data = md.data
        # logger.info('md.data', len(data['items']))
        return data

    def get_model_form_class(self):
        """
        获取ModelForm类
        :return:
        """
        # if self.model_form_class:
        #     return self.model_form_class

        if self.model_form_class:
            super_model_form_class = self.model_form_class
        else:
            super_model_form_class = forms.ModelForm

        class AddModelForm(super_model_form_class):
            class Meta:
                model = self.model_class
                fields = "__all__"
                # fields = ['facilityName']
                # labels = {"facilityName":"名字"}
                # error_messages ={
                #     "facilityName":{"required":"必填","invalid":"格式错误"}  ##自定义错误提示
                # }
        
            def __init__(self, *args, **kwargs):
                super(AddModelForm, self).__init__(*args, **kwargs)
                # name, field = list(self.fields.items())[0]
                # for x in dir(field):
                #     print('field[x]',name,type(field),dir(field))

                for name, field in self.fields.items():

                    # 对BooleanField、MultiSelectFormField做单独的样式处理
                    # from django.forms.fields import BooleanField
                    # from multiselectfield.forms.fields import MultiSelectFormField
                    # if not isinstance(field,(BooleanField,MultiSelectFormField)) :
                    #     field.widget.attrs['class'] = 'form-control form-control-sm'

                    field.widget.attrs['placeholder'] = field.help_text

        return AddModelForm


    def gen_request_data(self, request, pk):
        '''解析请求信息为dict并挂载到request.data
        
        [description]
        
        Arguments:
            request {[type]} -- [description]
            pk {int / string} -- 主键值
        
        Raises:
            Exception -- [description]
        '''
        if not settings.DEBUG and request.method not in ACCEPT_REQUEST_METHOD:
            raise Exception('为保护数据安全 暂不允许%s请求方法' % request.method)

        # 若为项目内的非http请求
        if request.content_type in ['python/dict',]:
            if isinstance(request.data, dict) and request.data.get('pk'):
                # 将pk值动态附加到主键值
                request.data[self.model_class._meta.pk.name] = request.data.get('pk')
        # 若为http请求
        else:
            if request.method == 'GET':
                # logger.info('GET')
                request.data = dict(request.data, **QueryDict.dict(request.GET))
            else:
                try:
                    body = json.loads(request.body)
                except Exception as e:
                    raise Exception('请求数据序列化出现异常 请确保格式为JSON', e)
                # 判断是否为允许的批量操作方法
                action_name = body.get('action')
                action_name_list = [func.__name__ for func in self.get_action_list()]
                # logger.info('action_name action_dict', action_name, action_name_list)
                if action_name:
                    if action_name not in action_name_list:
                        raise Exception('非法的操作方法(%s)' % action_name)

                    if not body.get('pk_list') and not isinstance(body.get('pk_list'), list):
                        raise Exception('指定操作方法的同时必须指定参数(pk_list) 且必须为一个list/array')

                elif request.method in ['PATCH', 'DELETE',] and not pk:
                    raise Exception('未指定操作方式的(%s)类型请求每次仅允许对单条数据进行操作 需在url中指定操作项主键值(通常为id)' % request.method)

                # 根据content_type解析请求数据为dict
                if request.content_type in ['application/json', 'text/plain']:
                    request.data = body
                
                elif request.content_type in ['multipart/form-data']:
                    # 转换form-data类型数据为dict
                    from django.http.multipartparser import MultiPartParser
                    query_dict, file = MultiPartParser(request.META, request, request.upload_handlers).parse()
                    request.data = QueryDict.dict(query_dict)

                else:
                    raise Exception('不支持的Content-Type: %s, 请确保使用此范围内的Content-Type: %s' % (request.content_type, str(['application/json', 'text/plain', 'multipart/form-data'])))

            if pk:
                # 将pk值动态附加到主键值
                request.data[self.model_class._meta.pk.name] = pk
                # logger.info('gen_request_data', request.data, body, pk)

        # if hasattr(request,'data'):
        #     print("if hasattr(request,'data')", type(request.data), request.data)

    def hook_get_after(self, request, pk=None):
        '''钩子函数: 在api成功查询一条或多条数据后执行
        '''
        pass

    def hook_post_before(self, request):
        '''钩子函数: 在api成功增加一条数据后执行
        '''
        pass

    def hook_post_after(self, request):
        '''钩子函数: 在api增加一条数据前执行
        '''
        pass

    def hook_patch_after(self, request, pk=None):
        '''钩子函数: 在api成功修改一条数据后执行
        '''
        pass

    def hook_delete_after(self, request, pk=None):
        '''钩子函数: 在api成功删除一条数据后执行
        '''
        pass

    def determine_version(self, request, *args, **kwargs):
        """
        If versioning is being used, then determine any API version for the
        incoming request. Returns a two-tuple of (version, versioning_scheme)
        """
        if self.versioning_class is None:
            return (None, None)
        scheme = self.versioning_class()
        return scheme.determine_version(request, *args, **kwargs)

    # @api_view(['GET'])  # rest_framework装饰器
    def api(self, request, pk=None, *args, **kwargs):
        """查询通用API(前后端分离版本)
        GET: 返回当前model所有数据, 若指定pk值则返回指定数据
        POST: 添加一条数据, 若request中含pk值则忽略pk值
        PATCH: 更新一条数据, 需指定pk值
        DELETE: 删除一条数据, 需指定pk值
        
        Arguments:
            request {[type]} -- [description]
            pk {int / string} -- 单条数据操作时所需要的主键值
        
        Returns:
            [type] -- [description]
        """
        version, allowed = self.determine_version(request, *args, **kwargs)
        # logger.info('version, scheme', version)
        if not allowed:
            return JsonResponse(
                utils.ApiResponse(-1, 'API版本[%s]不被允许.' % version, {}).__dict__,
                json_dumps_params={'ensure_ascii': False},
                )

        if not hasattr(request, 'data'): request.data = {}
        code = -1
        msg = None
        data = {}
        # print(
        #     'request', 
        #     request.method,
        #     request.content_type,
        #     request.content_params,
        #     # request.body,
        #     request.data,
        #     )

            
        try:
            # 解析请求信息为dict并挂载到request.data
            self.gen_request_data(request, pk)
        except Exception as e:
            msg = '解析请求数据时发生异常 请参考data中的提示信息'
            data[e.__class__.__name__] = str(e)
            return JsonResponse(
                utils.ApiResponse(code, msg=msg, data=data).__dict__,
                json_dumps_params={'ensure_ascii': False},
                )


        if request.method == 'POST':
            # from django.db import transaction
            # with transaction.atomic():
            try:
                # 触发基于signals自定义的钩子
                utils.post_before.send(sender=self.model_class, request=request)
                # lens自定义钩子
                # self.hook_post_before(request)
                AddModelForm = self.get_model_form_class()
                form = AddModelForm(request.data)
                if form.is_valid():
                    # utils.valid_after.send(sender=self.model_class, request=request, old_instance=None, form=form)

                    instance = form.save(commit=False)
                    utils.valid_after.send(sender=self.model_class, request=request, instance=instance)
                    instance.save()

                    # Django不支持序列化单个model对象
                    # 因此用单个对象来构造一个只有一个对象的数组(类似QuerySet对象)
                    # 由于序列化QuerySet会被'[]'所包围
                    # 因此使用string[1:-1]来去除由于序列化QuerySet而带入的'[]'
                    data = json.loads(serializers.serialize('json',[instance])[1:-1])
                    code = 1
                    msg = 'success'
                    # self.hook_post_after(request)
                else:
                    data = json.loads(form.errors.as_json())
            except Exception as e:
                msg = '处理%s请求时发生异常 请参考data中的提示信息' % request.method
                data[e.__class__.__name__] = str(e)
                data['Traceback'] = str(traceback.format_exc())

        
        elif request.method in ['GET', 'PATCH', 'DELETE',]:
            if request.method == 'GET':
                try:
                    data = self.get_model_data(request, pk=pk, pagination=self.is_pagination)
                    code = 1
                    msg = 'success'
                    # self.hook_get_after(request, pk=pk)
                    # print('LENS api GET', len(data['items']))
                except Exception as e:
                    msg = '处理%s请求时发生异常 请参考data中的提示信息' % request.method
                    data[e.__class__.__name__] = str(e)
                    data['Traceback'] = str(traceback.format_exc())
            else:
                if not pk:
                    # 若未指定pk就执行操作方法 request.data中是否包含action 已经在gen_request_data中进行了校验
                    action_name = request.data.get('action')
                    return getattr(self, action_name)(request)
                else:
                    # 指定了pk就进行常规单条数据的操作
                    # obj = self.model_class.objects.get(pk=pk)
                    obj = self.model_class.objects.filter(pk=pk).first()
                    if not obj:
                        msg = '数据表(%s)中无主键值为(%s)的项' % (self.model_class._meta.model_name, pk)
                    elif request.method == 'PATCH':
                        try:
                            utils.patch_before.send(sender=self.model_class, request=request, instance=obj)
                            # print('lens request', request.data)
                            # obj.update(**request.data)
                            # 针对单个对象 将update更换为__dict__.update + save 后可正常执行save钩子
                            # obj.__dict__.update(**request.data)
                            # obj.save()

                            AddModelForm = self.get_model_form_class()
                            for k,v in forms.models.model_to_dict(obj).items():
                                if k not in request.data: request.data[k] = v
                            form = AddModelForm(data=request.data, instance=obj)
                            if form.is_valid():
                                form.save(commit=False)
                                utils.valid_after.send(sender=self.model_class, request=request, instance=obj)
                                obj = form.save()
                                utils.patch_save.send(sender=self.model_class, request=request, instance=obj)

                                data = json.loads(serializers.serialize('json',[obj])[1:-1])
                                msg = '更新成功'
                                code = 1
                                # self.hook_patch_after(request, pk=pk)
                            else:
                                data = json.loads(form.errors.as_json())
                        except Exception as e:
                            msg = '处理(%s)请求时发生异常 请参考data中的提示信息' % request.method
                            data[e.__class__.__name__] = str(e)

                    elif request.method == 'DELETE':
                        logger.info('DELETE 2', request.data)
                        obj.delete()
                        msg = '删除成功'
                        code = 1
                        # self.hook_delete_after(request, pk=pk)

        # print('response.__dict__', data, response.__dict__)
        return JsonResponse(
            utils.ApiResponse(code, msg=msg, data=data).__dict__,
            json_dumps_params={'ensure_ascii': False},
            )

    def _api(self, method='GET', data={}):
        if not type(method) == str:
            raise Exception('关键词参数(method)类型请确保是String')
        else:
            method_upper = method.upper()
        if method_upper not in ACCEPT_REQUEST_METHOD:
            raise Exception('%s请求方法在当前环境下不被允许 前环境下被允许的method: %s' % (method, ACCEPT_REQUEST_METHOD))
        if not type(data) == dict:
            raise Exception('关键词参数(data)类型请确保是dict')

        # 直接调用lens内部封装的通用接口
        request = HttpRequest()
        # print('_api',
            # request.content_type,
            # request.body,
            # request.method,
            # request.data,
            # )
        request.content_type = 'python/dict'
        request.method = method_upper
        request.data = data
        response = self.api(request)
        return json.loads(response.content)


    def wrapper(self, func):
        @functools.wraps(func)
        def inner(request, *args, **kwargs):
            self.request = request
            return func(request, *args, **kwargs)

        return inner

    def get_urls(self):
        info = self.model_class._meta.app_label, self.model_class._meta.model_name

        urlpatterns = [
            url(r'^$', self.wrapper(self.api), name='%s_%s' % info),
        ]

        extra = self.extra_url()
        if extra:
            urlpatterns.extend(extra)

        return urlpatterns

    def extra_url(self):
        pass

    @property
    def urls(self):
        return self.get_urls()


class LensAPI:
    """JSON类型的API数据的入口类 对应django中的View视图类
    1. 校验version
    2. 获取当前路由中version对应的data_class
    3. 生成API数据
    4. 封装response返回给接口

    Static Attribute:
        versioning_class {class}: 校验版本的钩子类
        data_class {class}: 生成API数据的钩子类
        response_meta {dict}: 封装response的元数据
    """
    versioning_class = lens_settings.DEFAULT_VERSIONING_CLASS
    data_class = lens_settings.DEFAULT_SCHEMA_CLASS
    response_meta = {
        'code': 1,
        'msg': None,
        'data': {}
    }

    def __init__(
        self,
        # data_function=None,
        # schema_class=lens_settings.DEFAULT_SCHEMA_CLASS
    ):
        '''在实例化阶段可接受定制化参数 暂时废弃
        '''
        # self.data_function = data_function or self.data_function
        # self.schema_class = schema_class
        pass

    def determine_version(self, request, *args, **kwargs):
        """
        If versioning is being used, then determine any API version for the
        incoming request. Returns a two-tuple of (version, versioning_scheme)
        """
        if self.versioning_class is None:
            return (None, None)
        scheme = self.versioning_class()
        return scheme.determine_version(request, *args, **kwargs)

    def get_version_data_class(self, request, *args, **kwargs):
        '''获取符合version的生成API数据的类
        '''
        # 反射方式导入模块 第二个参数其实无用
        module = kwargs.get('module')
        data_class = kwargs.get('data_class')
        if not module or not data_class:
            raise Exception('参数(module、data_class)缺一不可')
        module = perform_import(module, 'lens')
        if not module:
            raise Exception('Lens中没有找到对应的模块(%s)' % ('module'))

        # 反射方式获取指定版本的模块
        version_module = getattr(module, request.version, None)
        if not version_module:
            raise Exception('(%s)模块中没有找到对应的版本(%s)' % (module.__name__, request.version))
        version_data_class = getattr(version_module, data_class)

        # 反射方式获取指定版本模块内的类
        if not version_data_class:
            raise Exception('对应(%s)版本的(%s)模块中没有找到名为(%s)的类' % (module.__name__, request.version, data_class))
        self.data_class = version_data_class

    def _response(self, request, *args, **kwargs):
        '''构造API数据所需的流程
        1. 校验version
        2. 获取当前路由中version对应的data_class
        3. 生成API数据

        Returns:
            [dict] -- [API数据]
        '''
        # 校验version
        request.version, request.version_allowed = self.determine_version(request, *args, **kwargs)
        # logger.info('version, allowed', request.version, request.version_allowed)
        if not request.version_allowed:
            raise Exception('API版本[%s]不被允许.' % request.version)

        # 获取当前路由中version对应的data_class
        self.get_version_data_class(request, *args, **kwargs)

        # 生成API数据
        return self.data_class().get_schema(request, *args, **kwargs)

    def response(self, request, *args, **kwargs):
        '''获取API数据 并封装response返回给接口

        Returns:
            [JsonResponse] -- [封装了API数据的response]
        '''

        # 获取API数据
        try:
            self.response_meta['data'] = self._response(request, *args, **kwargs)
        except Exception as e:
            self.response_meta['code'] = -1
            self.response_meta['msg'] = str(e)
            self.response_meta['data'] = {}

        # 封装response
        response = utils.ApiResponse(**self.response_meta)
        # print('response.__dict__', response.__dict__)
        return JsonResponse(
            response.__dict__,
            json_dumps_params={'ensure_ascii': False},
            )


class ModelAdmin(object):
    '''Lens入口类
    - 管理所有注册到lens中的model
    - 生成所管理model的schema、model所属app的schema
    - 自动分发url
    '''

    def __init__(self):
        self._registry = {}
        self.app_name = 'api'
        self.namespace = 'api'

    def register(self, model_class, model_config=None):
        """将model和model的config类对应起来, 封装到admin对象（单例模式）中
        
        [description]
        
        Arguments:
            model_class {Model} -- 单个model表类
        
        Keyword Arguments:
            model_config {ModelConfig} -- 与model表类对应的ModelConfig配置类 (default: {None})
        """
        if not model_config:
            model_config = ModelConfig
        self._registry[model_class] = model_config(model_class, self)

    def get_schema(self):

        urlpatterns = [
            url(
                r'^(?P<version>[v]{1}\d{1})/apps/$',
                LensAPI().response,
                {
                    'module': 'lens.schema',
                    'data_class': 'Apps',
                    'registry': self._registry,
                }
            ),
            url(
                r'^(?P<version>[v]{1}\d{1})/tables/$',
                LensAPI().response,
                {
                    'module': 'lens.schema',
                    'data_class': 'Models',
                    'registry': self._registry,
                }
            ),
            url(
                r'^(?P<version>[v]{1}\d{1})/(?P<app>\w+)/(?P<model>\w+)/$',
                LensAPI().response,
                {
                    'module': 'lens.schema',
                    'data_class': 'Model',
                }
            )
        ]

        extra = self.extra_schema(self)
        if extra:
            urlpatterns.extend(extra)

        return urlpatterns

    def extra_schema(self, *args, **kwargs):
        pass

    @property
    def schema(self):
        urls = self.get_schema(), 'schema', 'schema'
        return urls

    def get_api(self):

        urlpatterns = []

        for k, v in self._registry.items():
            app_label = k._meta.app_label
            model_name = k._meta.model_name
            urlpatterns.append(url(r'^(?P<version>[v]{1}\d{1})/%s/%s/' % (app_label, model_name,), (v.urls, None, None)))
            urlpatterns.append(url(r'^(?P<version>[v]{1}\d{1})/%s/%s/(?P<pk>\d+)' % (app_label, model_name,), (v.urls, None, None)))

        extra = self.extra_api(self)
        if extra:
            urlpatterns.extend(extra)

        return urlpatterns

    def extra_api(self, *args, **kwargs):
        # print('args kwargs', args,kwargs)
        pass

    @property
    def api(self):
        urls = self.get_api(), self.app_name, self.namespace
        return urls




lens = ModelAdmin()
setattr(lens, 'post_before', utils.post_before)
setattr(lens, 'patch_before', utils.patch_before)
setattr(lens, 'valid_after', utils.valid_after)
setattr(lens, 'patch_save', utils.patch_save)