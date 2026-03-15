# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'full_name', 'role', 'phone_number', 
                   'is_active', 'last_active', 'profile_picture_preview']
    list_filter = ['role', 'is_active', 'theme']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Info', {
            'fields': ('role', 'phone_number', 'profile_picture', 
                      'theme', 'last_active')
        }),
        ('Notifications', {
            'fields': ('notification_email', 'notification_sms')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Info', {
            'fields': ('role', 'phone_number', 'email', 'first_name', 'last_name')
        }),
    )
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Full Name'
    
    def profile_picture_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />',
                obj.profile_picture.url
            )
        return format_html('<span class="text-muted">No image</span>')
    profile_picture_preview.short_description = 'Picture'
    
    actions = ['make_admin', 'make_manager', 'make_staff', 'make_viewer']
    
    def make_admin(self, request, queryset):
        queryset.update(role='admin')
        self.message_user(request, f'{queryset.count()} users updated to Admin.')
    make_admin.short_description = 'Set selected users as Admin'
    
    def make_manager(self, request, queryset):
        queryset.update(role='manager')
        self.message_user(request, f'{queryset.count()} users updated to Manager.')
    make_manager.short_description = 'Set selected users as Manager'
    
    def make_staff(self, request, queryset):
        queryset.update(role='staff')
        self.message_user(request, f'{queryset.count()} users updated to Staff.')
    make_staff.short_description = 'Set selected users as Staff'
    
    def make_viewer(self, request, queryset):
        queryset.update(role='viewer')
        self.message_user(request, f'{queryset.count()} users updated to Viewer.')
    make_viewer.short_description = 'Set selected users as Viewer'

admin.site.register(User, CustomUserAdmin)