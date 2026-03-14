from django.contrib import admin
from .models import EmployeeSalary, Payslip

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'basic_pay',
        'hra',
        'cca',
        'sa',
        'medical_allowance',
        'effective_from',
    )

    ordering = ('-effective_from',)


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'month',
        'year',
        'total_earnings',
        'total_deductions',
        'net_salary',
    )

    list_filter = ('year', 'month')
    readonly_fields = (
        'employee',
        'month',
        'year',
        'basic_pay',
        'hra',
        'conveyance',
        'medical_allowance',
        'cca',
        'sa',
        'other_allowance',
        'total_earnings',
        'epf_deduction',
        'esi_deduction',
        'tds_deduction',
        'lop_deduction',
        'other_deductions',
        'total_deductions',
        'net_salary',
        'generated_date',
    )
