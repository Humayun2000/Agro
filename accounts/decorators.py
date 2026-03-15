# accounts/decorators.py
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles):
    """Decorator to restrict access based on user role"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('home')
        return wrapper
    return decorator

def admin_required(view_func):
    """Decorator for admin-only views"""
    return role_required(['admin'])(view_func)

def manager_required(view_func):
    """Decorator for manager+ views"""
    return role_required(['admin', 'manager'])(view_func)