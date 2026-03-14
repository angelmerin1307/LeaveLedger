from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import Employee


# ===============================
# Employee Inline (linked to User)
# ===============================
class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name = "Employee Profile"
    verbose_name_plural = "Employee Profile"


# ===============================
# Custom User Admin
# ===============================
class CustomUserAdmin(UserAdmin):
    inlines = (EmployeeInline,)

    list_display = (
        "username",
        "email",
        "is_staff",
        "is_superuser",
        "is_active",
    )


# ===============================
# Register Custom User Admin
# ===============================
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
