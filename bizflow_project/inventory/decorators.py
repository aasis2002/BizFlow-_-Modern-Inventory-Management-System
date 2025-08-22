# inventory/decorators.py
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from functools import wraps

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Access denied")
            
            # Get user role from profile
            user_role = getattr(request.user.userprofile, 'role', 'VIEWER')
            
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden("Access denied. Insufficient permissions.")
        return _wrapped_view
    return decorator

# Specific role decorators
admin_required = role_required(['ADMIN'])
manager_required = role_required(['ADMIN', 'MANAGER'])
staff_required = role_required(['ADMIN', 'MANAGER', 'STAFF'])