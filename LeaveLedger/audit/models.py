from django.db import models
from accounts.models import Employee

class AuditLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.TextField()
    module = models.CharField(max_length=50)

    timestamp = models.DateTimeField(auto_now_add=True)
