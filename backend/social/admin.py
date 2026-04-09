from django.contrib import admin

from .models import BlockedUser, Connection, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ('handle', 'user', 'display_name', 'visibility', 'created_at')
    search_fields = ('handle', 'display_name', 'user__email')
    list_filter   = ('visibility',)
    readonly_fields = ('created_at', 'updated_at', 'handle_changed_at')


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display  = ('id', 'from_user', 'to_user', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('from_user__email', 'to_user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display  = ('id', 'blocker', 'blocked', 'created_at')
    search_fields = ('blocker__email', 'blocked__email')
    readonly_fields = ('created_at',)
