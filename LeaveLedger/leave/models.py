from django.db import models
from accounts.models import Employee

from django.utils.timezone import now
from decimal import Decimal


class LeaveType(models.Model):
    leave_type_id = models.AutoField(primary_key=True)
    leave_name = models.CharField(max_length=20, unique=True)
    is_paid = models.BooleanField(default=True)
    max_per_year = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.leave_name

class LeaveApplication(models.Model):

   
    @property
    def is_half_day(self):
        from decimal import Decimal
        return self.total_days == Decimal("0.50")

    @property
    def display_status(self):
        today = now().date()
        if self.status == "Approved" and today > self.end_date:
            return "Completed"
        return self.status

    class Status(models.TextChoices):
        PENDING = "Pending"
        APPROVED = "Approved"
        REJECTED = "Rejected"
        CANCELLED = "Cancelled"
        


    leave_id = models.BigAutoField(primary_key=True)

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)

    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=4, decimal_places=2)

    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    is_auto_converted = models.BooleanField(default=False)
    applied_date = models.DateTimeField(auto_now_add=True)
    cancelled_by = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_leaves"
        )

    cancelled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Leave {self.leave_id} - {self.employee.emp_code}"

class LeaveApproval(models.Model):
    

    class Role(models.TextChoices):
        RM1 = "RM1", "Primary Manager"
        RM2 = "RM2", "Secondary Manager"
        HR = "HR", "HR"

    class Status(models.TextChoices):
        PENDING = "Pending"
        APPROVED = "Approved"
        REJECTED = "Rejected"

    approval_id = models.BigAutoField(primary_key=True)
    remarks = models.TextField(blank=True, null=True)


    leave = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="approvals"   # ✅ FIXED
    )


    

    approver = models.ForeignKey(Employee, on_delete=models.CASCADE)
    approver_role = models.CharField(max_length=5, choices=Role.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    remarks = models.TextField(blank=True)
    action_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("leave", "approver")
        ordering = ["approval_id"]



    
from decimal import Decimal

class LeaveBalance(models.Model):
    balance_id = models.BigAutoField(primary_key=True)

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()

    cl_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("18.00"))
    ml_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("6.00"))
    ol_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("3.00"))
    compoff_credit = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    lop_taken = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ('employee', 'year')