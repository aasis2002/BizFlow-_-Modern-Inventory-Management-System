from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django built-in admin (optional - you can keep it or remove it)
    path('django-admin/', admin.site.urls),
    
    # Include all inventory URLs (including your custom admin routes)
    path('', include('inventory.urls')),
    
    # Default authentication routes (if you want to keep them)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)