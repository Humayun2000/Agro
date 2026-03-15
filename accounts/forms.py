# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User

class DateInput(forms.DateInput):
    input_type = 'date'

class CustomUserCreationForm(UserCreationForm):
    """Modern registration form"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+8801XXXXXXXXX'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Style username field
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        
        # Style password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Remove help text
        self.fields['username'].help_text = None
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.phone_number = self.cleaned_data.get('phone_number', '')
        
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Modern login form"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username or email
            user = authenticate(
                request=self.request,
                username=username,
                password=password
            )
            if not user:
                # Try email authentication
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(
                        request=self.request,
                        username=user_obj.username,
                        password=password
                    )
                except User.DoesNotExist:
                    pass
            
            if not user:
                raise forms.ValidationError(
                    'Invalid username/email or password.',
                    code='invalid_login'
                )
            
            self.user_cache = user
        return self.cleaned_data


class CustomUserChangeForm(UserChangeForm):
    """Profile update form"""
    
    password = None  # Remove password field
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                 'phone_number', 'profile_picture', 'theme',
                 'notification_email', 'notification_sms')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'notification_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PasswordResetRequestForm(forms.Form):
    """Password reset request form"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('No user found with this email address.')
        return email