from django.db import models

class Holiday(models.Model):

    class HolidayType(models.TextChoices):
        COMPULSORY = "Compulsory"
        OPTIONAL = "Optional"
        WEEKEND = "Weekend"

    holiday_id = models.BigAutoField(primary_key=True)
    holiday_date = models.DateField(unique=True)
    holiday_name = models.CharField(max_length=100)
    holiday_type = models.CharField(
        max_length=20,
        choices=HolidayType.choices
    )

    def __str__(self):
        return f"{self.holiday_name} ({self.holiday_date})"
