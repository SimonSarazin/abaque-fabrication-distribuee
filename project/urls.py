from django.contrib import admin
from django.urls import path, include
from abaque import views as choice_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", choice_views.login_view, name="login"),
    path("logout/", choice_views.logout_view, name="logout"),
    path("register/", choice_views.register_view, name="register"),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("", include("abaque.urls")),
]
