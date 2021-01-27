# 基于signals自定义钩子
import django.dispatch

# 1. 定义钩子函数


def func(sender, request, **kwargs):
    pass


# 2. 定义信号
post_before = django.dispatch.Signal(providing_args=["args", "kwargs"])
# 3. 注册信号
post_before.connect(func)


def func(sender, request, instance, **kwargs):
    pass


patch_before = django.dispatch.Signal(providing_args=["args", "kwargs"])
patch_before.connect(func)


valid_after = django.dispatch.Signal(providing_args=["args", "kwargs"])
valid_after.connect(func)


patch_save = django.dispatch.Signal(providing_args=["args", "kwargs"])
patch_save.connect(func)
