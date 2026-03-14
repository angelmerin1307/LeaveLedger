from django.db import models
from accounts.models import Employee

class CompOff(models.Model):

    class Status(models.TextChoices):
        PENDING = "Pending"
        APPROVED = "Approved"
        REJECTED = "Rejected"
        CANCELLED = "Cancelled"   


    compoff_id = models.BigAutoField(primary_key=True)

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    work_date = models.DateField()
    hours_worked = models.PositiveIntegerField()

    year = models.PositiveIntegerField()  # derived from work_date
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.year:
            self.year = self.work_date.year
        super().save(*args, **kwargs)
class CompOffApproval(models.Model):

    class Role(models.TextChoices):
        RM1 = "RM1"
        RM2 = "RM2"
        HR = "HR"

    class Status(models.TextChoices):
        PENDING = "Pending"
        APPROVED = "Approved"
        REJECTED = "Rejected"
        CANCELLED = "Cancelled"   


    approval_id = models.BigAutoField(primary_key=True)

    compoff = models.ForeignKey(
        CompOff,
        on_delete=models.CASCADE,
        related_name="approvals"
    )

    approver = models.ForeignKey(Employee, on_delete=models.CASCADE)
    approver_role = models.CharField(max_length=10, choices=Role.choices, default=Role.RM1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    remarks = models.TextField(blank=True)
    action_date = models.DateTimeField(null=True, blank=True)
