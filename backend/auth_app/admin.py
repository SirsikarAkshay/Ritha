from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display   = ['email', 'first_name', 'last_name', 'is_email_verified',
                     'google_calendar_connected', 'apple_calendar_connected',
                     'outlook_calendar_connected', 'is_staff', 'created_at']
    list_filter    = ['is_email_verified', 'google_calendar_connected',
                     'apple_calendar_connected', 'outlook_calendar_connected',
                     'is_staff', 'is_active']
    search_fields  = ['email', 'first_name', 'last_name']
    ordering       = ['-created_at']
    actions        = ['mark_verified', 'resend_verification', 'sync_all_calendars']
    fieldsets      = (
        (None,            {'fields': ('email', 'password')}),
        ('Personal',      {'fields': ('first_name', 'last_name', 'timezone')}),
        ('Verification',  {'fields': ('is_email_verified', 'email_verification_token', 'email_token_created_at')}),
        ('Password Reset', {'fields': ('password_reset_token', 'password_reset_created_at'), 'classes': ('collapse',)}),
        ('Google Calendar',{'fields': ('google_calendar_connected', 'google_calendar_email', 'google_calendar_synced_at')}),
        ('Apple Calendar', {'fields': ('apple_calendar_connected', 'apple_calendar_username', 'apple_calendar_synced_at')}),
        ('Outlook Calendar',{'fields': ('outlook_calendar_connected', 'outlook_calendar_email', 'outlook_calendar_synced_at')}),
        ('Raw Tokens',     {'fields': ('google_calendar_token', 'outlook_calendar_token'), 'classes': ('collapse',)}),
        ('Preferences',   {'fields': ('style_profile',)}),
        ('Permissions',   {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    readonly_fields = ['email_token_created_at', 'password_reset_created_at',
                       'google_calendar_synced_at', 'apple_calendar_synced_at', 'outlook_calendar_synced_at']

    @admin.action(description='Mark selected users as email-verified')
    def mark_verified(self, request, queryset):
        from auth_app.email import mark_verified as do_verify
        for user in queryset:
            do_verify(user)
        self.message_user(request, f'{queryset.count()} user(s) marked as verified.')

    @admin.action(description='Sync all calendars for selected users')
    def sync_all_calendars(self, request, queryset):
        from calendar_sync.google_calendar import sync_events as google_sync
        from calendar_sync.apple_calendar  import sync_events as apple_sync
        from calendar_sync.outlook_calendar import sync_events as outlook_sync
        total = 0
        for user in queryset:
            if user.google_calendar_connected:  google_sync(user)
            if user.apple_calendar_connected:   apple_sync(user)
            if user.outlook_calendar_connected: outlook_sync(user)
            total += 1
        self.message_user(request, f'Calendar sync triggered for {total} user(s).')

    @admin.action(description='Resend verification email to selected users')
    def resend_verification(self, request, queryset):
        from auth_app.email import send_verification_email
        sent = sum(1 for u in queryset if not u.is_email_verified and send_verification_email(u))
        self.message_user(request, f'Verification email sent to {sent} user(s).')
    add_fieldsets  = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),
    )
