from django.contrib import admin
from .models import UserList, GootList


@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'name', 'is_public', 'goot_count', 'created_at', 'updated_at')
    search_fields = ('name', 'owner__username')
    list_filter = ('is_public',)


@admin.register(GootList)
class GootListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'userlist', 'created_at')
    search_fields = ('user__username', 'userlist__name')
