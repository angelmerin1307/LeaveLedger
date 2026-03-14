from django.urls import path
from . import views

urlpatterns = [
    path(
        "employee/payslips/",
        views.employee_payslips,
        name="employee_payslips"
    ),

    path(
        "employee/payslips/generate/",
        views.generate_payslip,
        name="generate_payslip"
    ),

    path(
        "hr/payslips/",
        views.hr_payslips,
        name="hr_payslips"
    ),
]
