from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User



class Employee(models.Model):

    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        HR = "HR", "HR"
        ADMIN = "ADMIN", "Admin"

    employee_id = models.BigAutoField(primary_key=True)

    emp_code = models.CharField(max_length=20, unique=True)

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    email = models.EmailField(unique=True)

    phone = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message="Phone number must contain exactly 10 digits"
            )
        ]
    )

    designation = models.CharField(max_length=100)

    date_of_joining = models.DateField()

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE
    )

    # Reporting structure
    pa = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='primary_reports'
    )
    sa = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='secondary_reports'
    )
    hr = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='hr_reports'
    )

    # Identity & statutory details
    pan_number = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
                message="Invalid PAN format"
            )
        ]
    )

    uan_number = models.CharField(
        max_length=12,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{12}$',
                message="UAN must be exactly 12 digits"
            )
        ]
    )

    # Bank details
    bank_name = models.CharField(max_length=100)
    account_holder_name = models.CharField(max_length=100)

    account_number = models.CharField(
        max_length=30,
        unique=True
    )

    ifsc_code = models.CharField(
        max_length=11,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{4}0[A-Z0-9]{6}$',
                message="Invalid IFSC code format"
            )
        ]
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.emp_code} - {self.first_name}"
    

    user = models.OneToOneField(
    User,
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='employee_profile'
)
