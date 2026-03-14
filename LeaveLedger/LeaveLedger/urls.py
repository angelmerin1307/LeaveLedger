from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.shortcuts import redirect

def root_redirect(request):
    return redirect("/accounts/login/")

urlpatterns = [
    # Homepage
    
    path("", root_redirect, name="root"),
    # Admin
    path("admin/", admin.site.urls),

    # Authentication (login, logout, password reset)
    path("accounts/", include("django.contrib.auth.urls")),

    # Accounts app URLs (dashboards, register, redirects)
    path("accounts/", include("accounts.urls")),
    path("payroll/", include("payroll.urls")),
    path("leave/", include("leave.urls")),
    path("compoff/", include("compoff.urls")),
    path("audit/", include("audit.urls")),
    path("calendar/", include("calendar_app.urls")),


]
