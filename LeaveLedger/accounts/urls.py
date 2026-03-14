from django.urls import path
from django.contrib.auth import views as auth_views
from leave.views import hr_calendar
from audit.views import audit_log_list
from calendar_app.views import manage_holidays


from .views import (
    post_login_redirect,
    employee_dashboard,
    my_profile,
    hr_dashboard,
    hr_create_employee,
    manage_employees,
    employee_detail,
    employee_edit,
    hr_apply_leave,
)

urlpatterns = [

    # ---------------------------
    # Redirect
    # ---------------------------
    path('redirect/', post_login_redirect, name='post_login_redirect'),

    # ---------------------------
    # Employee Area
    # ---------------------------
    path('employee/', employee_dashboard, name='employee_dashboard'),
    path('profile/', my_profile, name='my_profile'),

    path(
        "change-password/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/change_password.html"
        ),
        name="change_password"
    ),
    path(
        "change-password/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="accounts/change_password_done.html"
        ),
        name="password_change_done"
    ),

    # ---------------------------
    # HR Area (ALL grouped)
    # ---------------------------
    path('hr/', hr_dashboard, name='hr_dashboard'),

    path('hr/create-employee/', hr_create_employee, name='hr_create_employee'),
    path('hr/manage-employees/', manage_employees, name='manage_employees'),

    path('hr/employees/<int:employee_id>/', employee_detail, name='employee_detail'),
    path('hr/employees/<int:employee_id>/edit/', employee_edit, name='employee_edit'),
    path('hr/employees/<int:employee_id>/apply-leave/', hr_apply_leave, name='hr_apply_leave'),
    
    path("hr/calendar/", hr_calendar, name="hr_calendar"),
    path("hr/audit-logs/", audit_log_list, name="audit_logs"),
    path("hr/manage-holidays/", manage_holidays, name="manage_holidays"),

]
