from django.urls import include
from django.contrib import admin
from django.urls import path

from my_app.odata_urls import urlpatterns as odata_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    # Tous les endpoints OData (générés dynamiquement depuis odata_urls.py)
    path("odata/", include(odata_urlpatterns)),
]
