from django.db import transaction
# DJANGO_SETTINGS_MODULE = 'app.settings'
# from django.middleware.transaction import TransactionMiddleware
from django.conf import settings
settings.configure()
settings.DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '',  # noqa
        'USER': 'root',
        'PASSWORD': '',
        # 'HOST': 'localhost',
        'HOST': '192.168.101.100',
        'PORT': '3306',
    },
    # 'default': {    # sqlite
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
}


def foo():
    print('foo')
    raise Exception('foo raise')
    pass


def bar():
    print('bar')
    pass


try:
    with transaction.atomic():  # Outer atomic, start a new transaction
        transaction.on_commit(foo)
        try:
            with transaction.atomic():  # Inner atomic block, create a savepoint
                transaction.on_commit(bar)
                # Raising an exception - abort the savepoint
                # raise Exception('Inner raise')
        except Exception as e:
            print('Inner catch:', e)
        # raise Exception('Outer raise')
except Exception as e:
    print('Outer catch:', e)


# @transaction.atomic
# def main():

#     foo.save()
#     # transaction now contains a.save()

#     sid = transaction.savepoint()

#     bar.save()
#     # transaction now contains a.save() and b.save()

#     if want_to_keep_b:
#         transaction.savepoint_commit(sid)
#         # open transaction still contains a.save() and b.save()
#     else:
#         transaction.savepoint_rollback(sid)
#         # open transaction now contains only a.save()


# if __name__ == '__main__':
#     main()
