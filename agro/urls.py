from django.urls import path, include
from django.contrib import admin

urlpatterns = [
        path('', include('home.urls')),
        path('admin/', admin.site.urls),
        path('accounts/', include('accounts.urls')),
        path('fishery/', include('fishery.urls')),
        path('dairy/', include('dairy.urls')),
        path('api/', include('dairy.api_urls')),
]
