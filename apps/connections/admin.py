from django.contrib import admin
from .models import Follow, ConnectionRequest, Connection

admin.site.register(Follow)
admin.site.register(ConnectionRequest)
admin.site.register(Connection)
