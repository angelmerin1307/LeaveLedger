from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now

from .models import Payslip, EmployeeSalary
from leave.models import LeaveBalance
from accounts.models import Employee

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now

from .models import Payslip, EmployeeSalary
from leave.models import LeaveBalance
from accounts.models import Employee

def calculate_payslip_amounts(employee, month, year):
    salary = get_object_or_404(EmployeeSalary, employee=employee)

    # Get leave balance for LOP
    balance = LeaveBalance.objects.filter(
        employee=employee,
        year=year
    ).first()

    lop_days = balance.lop_taken if balance else 0

    # Gross salary
    gross_salary = (
        salary.basic_salary +
        salary.hra +
        salary.conveyance +
        salary.medical_allowance +
        salary.cca +
        salary.special_allowance +
        salary.other_allowance
    )

    # Per-day salary (assume 30 days)
    per_day_salary = gross_salary / 30

    # LOP deduction
    lop_deduction = per_day_salary * lop_days

    # Other deductions
    total_deductions = (
        salary.epf +
        salary.esi +
        salary.professional_tax +
        lop_deduction
    )

    net_salary = gross_salary - total_deductions

    return {
        "gross_salary": gross_salary,
        "lop_days": lop_days,
        "lop_deduction": lop_deduction,
        "total_deductions": total_deductions,
        "net_salary": net_salary,
    }
@login_required
def generate_payslip(request, employee_id=None):
    user_employee = request.user.employee_profile

    # If employee_id is passed → HR flow
    if employee_id:
        if user_employee.role != "HR":
            return redirect("employee_dashboard")
        employee = get_object_or_404(Employee, emp_id=employee_id)
    else:
        # Employee generating their own payslip
        employee = user_employee

    today = now()
    year = today.year
    month = today.month

    # Prevent duplicate payslip
    if Payslip.objects.filter(
        employee=employee,
        year=year,
        month=month
    ).exists():
        return redirect("employee_payslips")

    salary_data = calculate_payslip_amounts(employee, year, month)
    salary = employee.salary

    Payslip.objects.create(
        employee=employee,
        year=year,
        month=month,

        basic_salary=salary.basic_salary,
        hra=salary.hra,
        conveyance=salary.conveyance,
        medical_allowance=salary.medical_allowance,
        cca=salary.cca,
        special_allowance=salary.special_allowance,
        other_allowance=salary.other_allowance,

        gross_salary=salary_data["gross_salary"],

        epf=salary.epf,
        esi=salary.esi,
        professional_tax=salary.professional_tax,
        lop_deduction=salary_data["lop_deduction"],
        total_deductions=salary_data["total_deductions"],

        net_salary=salary_data["net_salary"],
        generated_on=today,
    )

    return redirect("employee_payslips")
@login_required
def employee_payslips(request):
    employee = request.user.employee_profile

    payslips = Payslip.objects.filter(
        employee=employee
    ).order_by("-year", "-month")

    return render(request, "payroll/employee_payslips.html", {
        "payslips": payslips
    })

@login_required
def hr_payslips(request):
    hr = request.user.employee_profile
    if hr.role != "HR":
        return redirect("employee_dashboard")

    payslips = Payslip.objects.select_related(
        "employee"
    ).order_by("-year", "-month")

    return render(request, "payroll/hr_payslips.html", {
        "payslips": payslips
    })
