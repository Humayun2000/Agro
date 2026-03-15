from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('viewer', 'Viewer'),
    )
    
    THEME_CHOICES = (
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    )
    
    # Profile Information
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager')
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    # Preferences
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='auto')
    notification_email = models.BooleanField(default=True)
    notification_sms = models.BooleanField(default=False)
    
    # Metadata
    last_active = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_manager(self):
        return self.role in ['admin', 'manager']
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def update_last_active(self):
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])