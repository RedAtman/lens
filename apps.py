import os

from django.apps import AppConfig
from django.conf import settings


class LensConfig(AppConfig):
    name = 'lens'

    def ready(self):
        # 当程序启动时 去每个app目录下找lens.py并加载
        from django.utils.module_loading import autodiscover_modules
        autodiscover_modules('lens')

        # 区分主进程/daemon进程
        if os.environ.get('RUN_MAIN', None) == 'true':
            if settings.DEBUG:
                print('\033[0;31m生产环境部署本项目请将项目中settings.DEBUG设置为False\033[0m')
