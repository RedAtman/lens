# Lens —— Django通用增删改查组件

个人工作中封装的作为rest_ramework的另一个替代。
本质上为一个django项目的app，拷贝到django项目中后，加入settings.INSTALLED_APPS即可，开箱即用。

## Feature
- 通用增删改查API:
    - 请求方法: 'GET', 'POST', 'PATCH', 'DELETE' 对应:查增改删。
    - 自定义表字段显示控制。
    - 全表字段模糊搜索。
    - 指定表字段精确匹配搜索。
    - 查询指定表字段最大、最小值。
    - 分页控制。
    - 自定义以指定字段进行排序。
- 数据结构API:
    - 查询指定app的所有model结构信息。
    - 查询指定app指定model的所有字段结构信息。


## Config
1. 将整个组件作为app拷贝进已有django项目中。
2. 注册: `settings.INSTALLED_APPS`中添加`lens.apps.LensConfig`。
3. 配置: 在需要使用lens插件的app内新建`lens.py`文件，在`lens.py`文件中对model进行配置，示例如下:

example:
    
    # 3.1 引入lens、及lens封装的model配置基类ModelConfig
    from lens import lens, ModelConfig
    # 引入需要使用lens的models
    from . import models

    # 3.2 model配置类:继承lens配置基类ModelConfig
    class FooConfig(ModelConfig):
        """数据表配置 其它表均可根据此来进行灵活配置 全部为可选项"""

        # 指定Form类: 若需定制当前表的ModelForm
        model_form_class = FooModelForm
        # 指定允许显示的字段
        list_display = []
        # 指定禁止显示的字段
        list_block = []
        # 指定模糊搜索的字段范围
        search_list = []
        # 指定以某些字段排序
        order_by = []
        # 指定批量动作
        # action_list = ['multi_delete']
        # 是否分页
        is_pagination = False
        # 序列化层数: 目前仅支持0-1
        depth = 1

    # 3.3 将需要使用lens的model及写好的对应配置类注册到lens插件 即可完成配置
    lens.register(models.Foo, FooConfig)
        # 第一个参数是准备注册到lens中的model:必须项
        # 第二个参数是上一步封装的配置类FooConfig:非必须项,若为空则使用基类ModelConfig的默认配置

4. 添加到项目的url

example:

    from lens import lens
    urlpatterns = [
        path('api/', lens.api), # 数据API
        path('schema/', lens.schema),   # 数据结构API
    ]


## Usage
### 请求方法
'GET', 'POST', 'PATCH', 'DELETE' 对应:查增改删

### API

app信息及结构API: 默认版本v1

    url: /schema/v1/apps
    method: 'GET'
    data: {}

指定app指定model的表结构API: 默认版本v1

    url: /schema/v1/<app>/<model>
    method: 'GET'
    data: {}

指定app指定model数据API: 默认版本v1

    url: /api/v1/<app>/<model>
    method: 'GET', 'POST', 'PATCH', 'DELETE'
    data: {}

    # GET: 定义请求参数 data若为空字典则返回全表所有数据(分页方式)
    data = {
        # 'pk': 1,    # 获取指定主键的那条数据
        # 'q': 1,   # 模糊搜索全表字段 或search_list中规定的字段范围
        # 'max': 'id',  # 返回指定字段的最大值的那条数据
        # 'min': 'id',  # 返回指定字段的最小值的那条数据
        # '当前model的任意字段名': '任意值',   # 返回匹配任意字段名与任意值的那条数据
    }

    # POST: 在data中以dict定义每个字段的值 因为是增加数据因此不支持定义pk
    data = {
        'field_name': 'value',
        ...
    }

    # PATCH: data中以dict方式定义要修改字段的值
    data = {
        'field_name': 'value',
        ...
    }
    # DELETE: data中以dict方式定义要删除项的pk值 不可定义其它字段
    data = {
        'pk': 1,
    }


### 后端项目内直接调用lens通用API
免除模拟Http请求访问接口

example:调用示例

    # 1. 获取lens插件中注册的model对象
    from . import models
    foo = lens._registry.get(models.Foo)

    # 2. 发送请求: response即为lens的API返回的数据
    response = foo._api('get', data)
        # 第一个参数是请求方法: 'GET', 'POST', 'PATCH', 'DELETE' 对应:查增改删
        # 第二个参数是请求参数: 参考API部分
