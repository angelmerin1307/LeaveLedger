from django.db import models
from accounts.models import Employee

class EmployeeSalary(models.Model):
    salary_id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    basic_pay = models.DecimalField(max_digits=10, decimal_places=2)
    hra = models.DecimalField(max_digits=10, decimal_places=2)
    conveyance = models.DecimalField(max_digits=10, decimal_places=2)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    cca = models.DecimalField(max_digits=10, decimal_places=2)
    sa = models.DecimalField(max_digits=10, decimal_places=2)
    other_allowance = models.DecimalField(max_digits=10, decimal_places=2)

    epf = models.DecimalField(max_digits=10, decimal_places=2)
    esi = models.DecimalField(max_digits=10, decimal_places=2)
    tds = models.DecimalField(max_digits=10, decimal_places=2)

    effective_from = models.DateField()

    def __str__(self):
        return f"Salary Structure - {self.employee.emp_code}"


class Payslip(models.Model):
    payslip_id = models.BigAutoField(primary_key=True)

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.PositiveIntegerField()
    year = models.PositiveIntegerField()

    # ===== Earnings =====
    basic_pay = models.DecimalField(max_digits=10, decimal_places=2)
    hra = models.DecimalField(max_digits=10, decimal_places=2)
    conveyance = models.DecimalField(max_digits=10, decimal_places=2)
    medical_allowance = models.DecimalField(max_digits=10, decimal_places=2)
    cca = models.DecimalField(max_digits=10, decimal_places=2)
    sa = models.DecimalField(max_digits=10, decimal_places=2)
    other_allowance = models.DecimalField(max_digits=10, decimal_places=2)

    total_earnings = models.DecimalField(max_digits=10, decimal_places=2)

    # ===== Deductions =====
    epf_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    esi_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    tds_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    lop_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2)

    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)

    # ===== Final =====
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    generated_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')

    def __str__(self):
        return f"Payslip {self.month}/{self.year} - {self.employee.emp_code}"
