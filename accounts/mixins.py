# accounts/mixins.py
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin

class RoleRequiredMixin(AccessMixin):
    """Mixin to restrict access based on user role"""
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.role in self.allowed_roles:
            return super().dispatch(request, *args, **kwargs)
        
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')

class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin for admin-only views"""
    allowed_roles = ['admin']

class ManagerRequiredMixin(RoleRequiredMixin):
    """Mixin for manager+ views"""
    allowed_roles = ['admin', 'manager']