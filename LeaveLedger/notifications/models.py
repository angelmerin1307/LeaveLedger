from django.db import models
from accounts.models import Employee

class Notification(models.Model):
    notification_id = models.BigAutoField(primary_key=True)

    user = models.ForeignKey(Employee, on_delete=models.CASCADE)
    message = models.TextField()
    type = models.CharField(max_length=30)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
