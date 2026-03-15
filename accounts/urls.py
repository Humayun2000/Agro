# accounts/urls.py
from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             success_url=reverse_lazy('accounts:password_reset_done')
         ), name='password_reset'),
    
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url=reverse_lazy('accounts:password_reset_complete')
         ), name='password_reset_confirm'),
    
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), name='password_reset_complete'),
    
    # Admin Only
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/role/', views.user_role_update_view, name='user_role_update'),
]