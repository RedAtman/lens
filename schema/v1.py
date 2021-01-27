# from lens.schema.app import AppSchema, ModelSchema

from django.conf import settings
from django.apps import apps

from lens import utils
from lens.utils import logger

__all__ = ['Apps', 'Models', 'Model']


class BaseSchema(object):
    """docstring for BaseSchema"""

    # def __init__(self):
    #     # self.schema = self.get_schema()
    #     self.apps = self.get_apps()
    #     self.models = self.get_models()
    #     print('self.models', self.apps, self.models)

    # def get_apps(self):
    #     # get complete list of all apps
    #     # app_name.split('.')[-1] we need, because some system apps has dots in name
    #     # like 'django.contrib.admin', and app_label is 'admin'

    #     # 方式1 未排除自有app
    #     for app in apps.get_app_configs():
    #         print(app.verbose_name, ":", app)

    #     # 方式2 有bug
    #     list_of_apps = [apps.get_app_config(app_name.split('.')[-1])
    #                     for app_name in settings.INSTALLED_APPS]
    #     return list_of_apps

    # def get_models(self):
    #     # get list of models for one specific app. For example first app in list_of_apps
    #     models_list = [model for name, model in list_of_apps[0].models.items()
    #                    if not model._meta.auto_created]
    #     return models_list

    def get_schema(self, *args, **kwargs):
        msg = '{cls}.get_schema() must be implemented.'
        raise NotImplementedError(msg.format(
            cls=self.__class__.__name__
        ))


class Schema(BaseSchema):

    def get_schema(self, *args, **kwargs):
        logger.info('Schema get_schema', )
        schema = {}
        for model, config in registry.items():
            t = {
                'name': model._meta.model_name,
                'label': model._meta.verbose_name,
            }
            if not schema.get(model._meta.app_label, []):
                schema[model._meta.app_label] = {
                    'name': model._meta.app_label,
                    'label': model._meta.app_config.verbose_name,
                    'info': model._meta.app_config.info,
                    'tables': {
                        model._meta.model_name: t
                    }
                }
            else:
                schema[model._meta.app_label]['tables'][model._meta.model_name] = t
        logger.info('Schema get_schema', schema)
        return schema


class Apps(BaseSchema):
    """生成所有注册到lens中的model 及其所属app信息的schema
    """

    # def __init__(self, registry):
    # super(AppSchema, self).__init__()

    def get_schema(self, request, *args, **kwargs):
        '''返回当前lens中注册的所有app,model
        '''
        registry = kwargs.get('registry')
        # logger.info('Apps get_schema', args, kwargs)
        schema = {}
        for model, config in registry.items():
            t = {
                'name': model._meta.model_name,
                'label': model._meta.verbose_name,
            }
            if not schema.get(model._meta.app_label, []):
                schema[model._meta.app_label] = {
                    'name': model._meta.app_label,
                    'label': model._meta.app_config.verbose_name,
                    'info': model._meta.app_config.info,
                    'tables': {}
                }
            schema[model._meta.app_label]['tables'][model._meta.model_name] = t
        # logger.info('AppSchema get_schema', schema)
        return schema


class Models(BaseSchema):
    """生成所有注册到lens中的model的schema
    """

    # def __init__(self, registry):
    # super(ModelSchema, self).__init__()

    def get_schema(self, request, *args, **kwargs):
        '''返回当前lens中注册的所有app,model
        '''
        registry = kwargs.get('registry')
        # logger.info('Tables get_schema', args, kwargs)
        schema = {}
        table = []
        for model, config in registry.items():
            t = {
                'app': model._meta.app_label,
                'table': model._meta.model_name,
                'label': model._meta.verbose_name,
            }
            table.append(t)
        schema['table'] = table
        # logger.info('ModelSchema get_schema', schema)
        return schema


# 生成指定app下指定model的schema

import datetime

from django.apps import apps
from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.forms import ModelForm, DateTimeField
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models.fields.related import ForeignKey
from django.db.models.fields.reverse_related import ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel


MAPPING_FIELDS = {
    "AutoField": {
        'type': 'number',
        'suffix': ''
    },
    "FloatField": {
        'type': 'number',
        'suffix': ''
    },
    "DecimalField": {
        'type': 'number',
        'suffix': ''
    },
    "IntegerField": {
        'type': 'number',
        'suffix': ''
    },
    "SmallIntegerField": {
        'type': 'number',
        'suffix': ''
    },
    "BigIntegerField": {
        'type': 'number',
        'suffix': ''
    },
    "PositiveIntegerField": {
        'type': 'number',
        'suffix': ''
    },
    "PositiveSmallIntegerField": {
        'type': 'number',
        'suffix': ''
    },
    "GenericIPAddressField": {
        'type': 'textfield',
        'suffix': ''
    },
    # "BinaryField": "",
    "BooleanField": {
        'type': 'checkbox',
        'suffix': ''
    },
    "NullBooleanField": {
        'type': 'checkbox',
        'suffix': ''
    },
    "CharField": {
        'type': 'textfield',
        'suffix': ''
    },
    "TextField": {
        'type': 'textarea',
        'suffix': ''
    },
    "TimeField": {
        'type': 'time',
        'suffix': ''
    },
    "DateField": {
        'type': 'date',
        'suffix': ''
    },
    "DateTimeField": {
        'type': 'datetime',
        'suffix': '<i style="" class="fa fa-calendar" ref="icon"></i>'
    },
    # "DurationField": "",
    # "FileField": "",
    # "SlugField": "",
    # "UUIDField": "",
    'OneToOneField': {
        'type': 'number',
        'suffix': ''
    },
    'JSONField': {
        # 'type': 'json',
        'type': 'textarea',
        'suffix': ''
    },
    'ForeignKey': {
        'type': 'select',
        'suffix': ''
    },
    'OneToOneRel': {
        'type': 'textarea',
        'suffix': ''
    },
    'ManyToManyRel': {
        'type': 'textarea',
        'suffix': ''
    },
    'ManyToOneRel': {
        'type': 'textarea',
        'suffix': ''
    },
}

HTML_INPUT_ELEMENT_TYPE = [
    'text',
    'number',
    'email',
    'url',
    'password',
    'date',
    'time',
    'file',
    'checkbox',
    'datetime-local'
]


class FieldMeta(object):
    """ 获取Field的各种attribute的值
    """

    @classmethod
    def __call__(self, field, meta):
        try:
            if not hasattr(self, meta):
                raise Exception('尚未定义处理此meta(%s)的方法' % meat)
            return getattr(self, meta)(self, field)
        except Exception as e:
            # logger.info('FieldMeta', e, type(field), field, meta, getattr(self, meta))
            raise Exception(e)
            pass

    def label(self, field):
        return field.formfield().label or field.name or ''

    def required(self, field):
        return field.formfield().required or None

    def help_text(self, field):
        return field.formfield().help_text or ''

    def suffix(self, field):
        return MAPPING_FIELDS.get(
            field.__class__.__name__, '').get('suffix', '')

    def defaultValue(self, field):
        initial = ''
        try:
            initial = field.formfield().initial
            if callable(initial):
                if isinstance(field.formfield(), DateTimeField):
                    if isinstance(initial(), datetime.datetime):
                        initial = initial().strftime("%Y-%m-%d %H:%I:%S %Z")
        except:
            pass
        return initial


class Model(BaseSchema):
    """生成指定app下指定model的schema
    """

    # def __init__(self, registry):
    # super(ModelSchema, self).__init__()

    def get_formatted_app_name(self, app_name):
        # ToDo @bikesh "Just in case if you are are versioning your apps like apps/v1/ need to make this dynamic and optimise  "
        # print('app_name', app_name)
        app_name = app_name.split("apps.v1.")[-1]
        # print('app_name', app_name)
        return app_name

    def get_models(self, app_name):
        """
        app_name must match the  name of the AppConfig Class located in apps.py as below.
        from django.apps import AppConfig
        class CoreConfig(AppConfig):
            name = 'core'
        :param app_name: 'core'
        :return: "List of models linked with this app
        """
        try:
            models = list(apps.get_app_config(app_name).get_models())
            return models
        except:
            raise LookupError(f"this is no such app {app_name}")

    def get_model_form_fields(self, _model):
        ''' 生成前端可显示的fields
        '''
        class DynamicModelForm(ModelForm):
            class Meta:
                model = _model
                fields = "__all__"

        form = DynamicModelForm()
        model_form_fields = set(form.fields)

        return model_form_fields

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        app_name = kwargs.get('app_name')
        _models = self.get_models(app_name)

        forms = {}
        for _model in _models:
            fields = _model._meta.get_fields()
            model_form_fields = self.get_model_form_fields(_model)
            for f in fields:
                setattr(f, 'is_in_default_model_form_fields',
                        True if f.name in model_form_fields else False)
            forms.update({
                _model.__name__: fields
            })
        ctx['forms'] = forms
        ctx['app_name'] = app_name
        # print('get_context_data', ctx)
        return ctx

    def get_schema(self, request, *args, **kwargs):
        '''返回指定app,model的schema
        '''
        # context = self.get_context_data(**kwargs)
        app = kwargs.get('app', None)
        model = kwargs.get('model', None)
        # logger.info('ModelSchema get_schema', app, model)
        if not app and not model:
            raise Exception('未匹配到合法url')
        app_config = apps.get_app_config(app)
        model = app_config.get_model(model)
        # logger.info('app_config', type(app_config), app_config)

        self.app_name = self.get_formatted_app_name(app_config.name)
        self.model_name = model.__name__

        model_schema = self.get_model_schema(app_config, model)
        return model_schema
        # return super().get(request, *args, **kwargs)

    def get_model_schema(self, app, model):
        """
        This method will called when user submit the form. From the form we will get, model, selected fields and data_format style
        :param app: App name
        :param model: Model object
        :return: schema
        """
        model_schema = {
            'app': {
                'name': model._meta.app_label,
                'label': model._meta.app_config.verbose_name,
            },
            'name': model._meta.model_name,
            'label': model._meta.verbose_name,
            'components': []
        }

        for field in model._meta.get_fields():
            # 排除不需要在前端构建form的field: id、反向关联field
            # print('field', type(field), field)
            if field.name == 'id':
                continue
            if isinstance(field, ForeignObjectRel):
                # logger.info("ForeignObjectRel", field)
                continue

            component = self.get_field_data(model, field)
            # logger.info('component', component)
            model_schema['components'].append(component)
        # print('get_model_schema', model_schema)
        return model_schema
        # return JsonResponse(model_schema)

    def get_choices(self, choices):
        values = []
        for k, v in choices:
            values.append({
                "label": v,
                "value": k,
            })
        return values

    def get_html_element_data(self, field):
        try:
            widget = field.formfield().widget
        except:
            widget = ''
        form_field_type = field.formfield().__class__.__name__ if hasattr(
            field, 'formfield') else '',
        widget_class = widget.__class__.__name__
        if widget:
            data = {
                'element_type': '',
                'form_field_type': form_field_type,
                'widget': {
                    'attrs': widget.attrs if hasattr(widget, 'attrs') else '',
                    'widget_class': widget_class,
                }
            }
            if hasattr(widget, 'allow_multiple_selected'):
                data['widget']['allow_multiple_selected'] = widget.allow_multiple_selected
            if hasattr(widget, 'format'):
                data['widget']['format'] = widget.format

            if hasattr(widget, 'choices'):
                if form_field_type in ['ModelMultipleChoiceField', 'ModelChoiceField']:
                    data['widget']['can_be_autocomplete'] = True
                    data['widget']['set_id_on_form_save'] = True
                    data['widget']['form_field_type_for_reference'] = form_field_type
                else:
                    data['widget']['choices'] = self.get_choices(
                        widget.choices)

            if hasattr(widget, 'input_type'):
                input_type = widget.input_type
                if widget_class == 'DateTimeInput':
                    input_type = 'datetime-local'
                if widget_class == 'DateInput':
                    input_type = 'date'
                if widget_class == 'TimeInput':
                    input_type = 'time'
                element_type = ''
                if input_type in HTML_INPUT_ELEMENT_TYPE:
                    element_type = 'input'
                if input_type == 'select':
                    element_type = 'select'

                data['element_type'] = element_type
                data['widget'].update({
                    'type': input_type,

                })

            if widget_class == 'Textarea':
                data['element_type'] = 'textarea'
            print('get_html_element_data', data)
            return data
        else:
            return ''

    def get_field_data(self, model, field):
        data = {}
        try:
            data = self._get_field_data(model, field)
            if hasattr(field, 'base_field'):
                # if hasattr(field_obj, 'base_field') and isinstance(field_obj, ArrayField) and isinstance(
                #         field.formfield(),
                #         SimpleArrayField):
                # logger.info("hasattr(field, 'base_field')", field)
                data[field.name].update({
                    'base_field': self._get_field_data(model, field.base_field)
                })
        except FieldDoesNotExist:
            pass

        return data

    def _get_field_data(self, model, field):
        # print('field', field, type(field), field.__class__.__name__,
        #       MAPPING_FIELDS.get(field.__class__.__name__))
        field_type = MAPPING_FIELDS.get(field.__class__.__name__).get('type')
        field_schema = {
            "related_model": field.related_model._meta.model_name if hasattr(field.related_model, '_meta') else None,
            "is_relation": field.is_relation,
            "key": field.name,
            "type": field_type,
            "label": FieldMeta()(field, 'label'),
            "defaultValue": FieldMeta()(field, 'defaultValue'),
            "placeholder": FieldMeta()(field, 'help_text'),
            # "form_field_type": field.formfield().__class__.__name__ if hasattr(field, 'formfield') else '',
            # "html_form_element": self.get_html_element_data(field),
            # "is_in_default_model_form_fields":True if field.name in model_form_fields else False,
            "prefix": FieldMeta()(field, 'label'),
            'suffix': FieldMeta()(field, 'suffix'),
            # Is in ModelForm field which return __all__
            "validate": {
                "required": FieldMeta()(field, 'required'),
                "minLength": getattr(field, 'min_length', None),
                "maxLength": getattr(field, 'max_length', None),
            },
        }
        if isinstance(field, ForeignKey):
            # print('field', field.related_model._meta.__dict__)
            field_schema['dataSrc'] = 'url'
            field_schema['template'] = '<span>{{ item' + '.' + \
                field.related_model._meta.pk.name + ' }}</span>'
            field_schema['selectValues'] = 'data.items'
            field_schema['valueProperty'] = field.related_model._meta.pk.name
            field_schema['lazyLoad'] = False
            # field_schema['lazyLoad'] = True
            field_schema['data'] = {
                # 'url': 'api/v1/' + self.app_name + '/' + field.name
                'url': 'api/v1/' + self.app_name + '/' + field.related_model._meta.model_name
            }

        if hasattr(field, 'choices') and getattr(field, 'choices'):
            field_schema['data'] = {
                'values': self.get_choices(field.choices)
            }
            field_schema['type'] = 'select'
            field_schema['dataSrc'] = 'values'
            field_schema['template'] = '<span>{{ item.label }}</span>'

        return field_schema


# 进行缓存处理 优化程序资源占用及优化效率 以下代码暂时未使用

classes_cache = {}
instances_cache = {}

def inject_classes_cache():
    for name, klass in globals().items():
        if type(klass) == type and issubclass(klass, BaseSchema) and klass != BaseSchema:
            # print('name, klass ', type(name), type(klass), name, klass )
            classes_cache[name] = klass
            # 实例缓存的对象有一些问题 app model不匹配时返回的还是上一次实例化对象的数据
            instances_cache[name.lower()] = klass()

inject_classes_cache()
# print(
#     'classes_cache', classes_cache,
#     'instances_cache', instances_cache
#     )

def get_cls(schema_name: str):
    cls = classes_cache.get(schema_name)
    if cls:
        return cls
    raise TypeError('没有 {} 这个名字的类'.format(schema_name))