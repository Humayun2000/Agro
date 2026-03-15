from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.contrib.auth.views import LoginView, PasswordResetView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Q
from .models import User
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm,
    CustomUserChangeForm, PasswordResetRequestForm
)

# ==================== REGISTRATION VIEW ====================

@csrf_protect
@ensure_csrf_cookie
def register_view(request):
    """Modern registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Auto-login after registration (optional)
            login(request, user)
            
            messages.success(
                request, 
                f'🎉 Welcome {user.username}! Your account has been created successfully.'
            )
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'title': 'Create Account'
    })


# ==================== LOGIN VIEW ====================

class CustomLoginView(LoginView):
    """Modern login view"""
    form_class = CustomAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # Update last active timestamp
        if self.request.user.is_authenticated:
            self.request.user.update_last_active()
        
        # Redirect based on role
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        
        if self.request.user.is_admin:
            return reverse_lazy('admin_dashboard')
        elif self.request.user.is_manager:
            return reverse_lazy('accounts:dashboard')
        else:
            return reverse_lazy('home:dashboard')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username/email or password.')
        return super().form_invalid(form)


# ==================== LOGOUT VIEW ====================

def logout_view(request):
    """Logout view with message"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('home')


# ==================== PROFILE VIEWS ====================

@login_required
def profile_view(request):
    """View user profile"""
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'title': 'My Profile'
    })


@login_required
def profile_edit_view(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'title': 'Edit Profile'
    })


# ==================== DASHBOARD VIEW ====================

@login_required
def dashboard_view(request):
    """User dashboard with overview"""
    context = {
        'user': request.user,
        'title': 'Dashboard',
        'last_login': request.user.last_login,
        'days_since_joined': (timezone.now().date() - request.user.date_joined.date()).days,
    }
    return render(request, 'accounts/dashboard.html', context)


# ==================== ADMIN VIEWS ====================

@login_required
def user_list_view(request):
    """List all users (admin only)"""
    if not request.user.is_admin:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')
    
    users = User.objects.all().order_by('-date_joined')
    
    # Search
    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    
    # Filter by role
    role = request.GET.get('role')
    if role:
        users = users.filter(role=role)
    
    context = {
        'users': users,
        'title': 'User Management',
        'total_users': users.count(),
        'admins': users.filter(role='admin').count(),
        'managers': users.filter(role='manager').count(),
        'staff': users.filter(role='staff').count(),
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
def user_detail_view(request, user_id):
    """View user details (admin only)"""
    if not request.user.is_admin:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('home')
    
    user = get_object_or_404(User, id=user_id)
    
    context = {
        'profile_user': user,
        'title': f'User: {user.username}'
    }
    return render(request, 'accounts/user_detail.html', context)


@login_required
def user_role_update_view(request, user_id):
    """Update user role (admin only)"""
    if not request.user.is_admin:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(User.ROLE_CHOICES):
            user.role = new_role
            user.save()
            messages.success(request, f'Role updated to {user.get_role_display()}.')
    
    return redirect('accounts:user_detail', user_id=user.id)


# ==================== SETTINGS VIEW ====================

@login_required
def settings_view(request):
    """User settings/preferences"""
    if request.method == 'POST':
        # Update notification preferences
        request.user.notification_email = request.POST.get('notification_email') == 'on'
        request.user.notification_sms = request.POST.get('notification_sms') == 'on'
        request.user.theme = request.POST.get('theme', 'auto')
        request.user.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('accounts:settings')
    
    return render(request, 'accounts/settings.html', {
        'user': request.user,
        'title': 'Settings'
    })