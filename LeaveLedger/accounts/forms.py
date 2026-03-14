from django import forms
from .models import Employee

class HRCreateEmployeeForm(forms.ModelForm):

    class Meta:
        model = Employee
        fields = [
            # Basic
            "emp_code",
            "first_name",
            "last_name",
            "email",
            "phone",
            "designation",
            "date_of_joining",

            # Reporting
            "pa",   # primary approver
            "sa",   # secondary approver
            "hr",

            # Statutory
            "pan_number",
            "uan_number",

            # Bank
            "bank_name",
            "account_holder_name",
            "account_number",
            "ifsc_code",
        ]
        widgets = {
            "date_of_joining": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }



class EmployeeEditForm(forms.ModelForm):

    pa = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        label="Primary Approver (RM1)"
    )

    sa = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        label="Secondary Approver (RM2)"
    )

    hr = forms.ModelChoiceField(
        queryset=Employee.objects.filter(role="HR", is_active=True),
        required=False,
        label="HR Approver"
    )

    class Meta:
        model = Employee
        fields = [
            # basic info
            "first_name", "last_name", "email", "phone",

            # job info
            "designation", "role", "date_of_joining", "is_active",

            # reporting
            "pa", "sa", "hr",

            # bank & statutory
            "bank_name", "account_holder_name", "account_number",
            "ifsc_code", "pan_number", "uan_number",
        ]

        widgets = {
            "date_of_joining": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }