# cinema_service/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),

    # >> TUDO que começar com /api/cinema/ vai para as rotas do app 'cinema'
    path("api/cinema/", include("cinema.urls")),

    # Login/logout do DRF na API browser (útil para testes com sessão)
    path("api-auth/", include("rest_framework.urls")),
]

# Debug Toolbar (apenas em DEBUG)
if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
