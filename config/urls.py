from django.contrib import admin
from django.urls import include, path

# As imagens enviadas (/media/...) são entregues pela view loja.views.midia.
urlpatterns = [
    path("admin/", admin.site.urls),
    path("conta/", include("contas.urls")),
    path("", include("loja.urls")),
]
