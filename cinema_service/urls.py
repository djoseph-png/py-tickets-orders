# cinema_service/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/cinema/", include("cinema.urls")),
    path("api-auth/", include("rest_framework.urls")),  # login/logout do DRF
]

# Debug Toolbar (apenas em desenvolvimento)
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
