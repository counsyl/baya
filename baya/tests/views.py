from django.http import HttpResponse

from baya import requires
from baya import RolesNode as g

A = g('a')
AA = g('aa')
AAA = g('aaa')
B = g('b')


@requires((AA | B), get=AAA, post=A)
def my_view(request):
    return HttpResponse("my_view response")


def my_undecorated_view(request):
    return HttpResponse("my_undecorated_view response")


def query_param_view(request, name):
    return HttpResponse("query_param_view(%s) response" % name)
