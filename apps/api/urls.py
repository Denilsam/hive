from django.urls import path
from django.http import JsonResponse

app_name = 'api'


def api_root(request):
    return JsonResponse({
        "name": "Hive API",
        "version": "1.0.0",
        "description": "Hive skills. Create opportunities."
    })


urlpatterns = [
    path('', api_root, name='root'),
]
