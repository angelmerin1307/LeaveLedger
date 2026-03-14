from django.core.mail import send_mail
from django.conf import settings


def send_notification(subject, message, recipients):

    recipients = [email for email in recipients if email]

    if not recipients:
        return

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=True
    )


# -------------------------------------------------
# LEAVE EVENTS
# -------------------------------------------------

def leave_applied_email(leave):

    employee = leave.employee

    recipients = [
        employee.pa.email if employee.pa else None,
        employee.sa.email if employee.sa else None,
        employee.hr.email if employee.hr else None,
    ]

    subject = f"New Leave Request - {employee.first_name}"

    message = f"""
Employee: {employee.first_name} {employee.last_name}
Type: {leave.leave_type.leave_name}

Start Date: {leave.start_date}
End Date: {leave.end_date}
Days: {leave.total_days}

Reason:
{leave.reason}

Status: Pending
"""

    send_notification(subject, message, recipients)


def leave_edited_email(leave, old_start, old_end, old_type):

    employee = leave.employee

    recipients = [
        employee.pa.email if employee.pa else None,
        employee.sa.email if employee.sa else None,
        employee.hr.email if employee.hr else None,
    ]

    subject = f"Leave Updated - {employee.first_name}"

    message = f"""
Employee: {employee.first_name} {employee.last_name}

OLD DETAILS
Type: {old_type}
Dates: {old_start} → {old_end}

UPDATED DETAILS
Type: {leave.leave_type.leave_name}
Dates: {leave.start_date} → {leave.end_date}
Days: {leave.total_days}

Reason:
{leave.reason}
"""

    send_notification(subject, message, recipients)


def leave_cancelled_email(leave):

    employee = leave.employee

    recipients = [
        employee.pa.email if employee.pa else None,
        employee.sa.email if employee.sa else None,
        employee.hr.email if employee.hr else None,
    ]

    subject = f"Leave Cancelled - {employee.first_name}"

    message = f"""
Employee: {employee.first_name} {employee.last_name}

Leave Cancelled

Type: {leave.leave_type.leave_name}
Dates: {leave.start_date} → {leave.end_date}
Days: {leave.total_days}
"""

    send_notification(subject, message, recipients)


def leave_status_email(leave, approver, action):

    employee = leave.employee

    recipients = [
        employee.email,
        employee.pa.email if employee.pa else None,
        employee.sa.email if employee.sa else None,
        employee.hr.email if employee.hr else None,
    ]

    subject = f"Leave {action} - {employee.first_name}"

    message = f"""
Leave {action}

Employee: {employee.first_name} {employee.last_name}
Approved/Rejected by: {approver.first_name}

Type: {leave.leave_type.leave_name}
Dates: {leave.start_date} → {leave.end_date}
Days: {leave.total_days}

Status: {leave.status}
"""

    send_notification(subject, message, recipients)


# -------------------------------------------------
# COMPOFF EVENTS
# -------------------------------------------------

def compoff_applied_email(compoff):

    employee = compoff.employee

    recipients = [
        employee.pa.email if employee.pa else None,
        employee.sa.email if employee.sa else None,
        employee.hr.email if employee.hr else None,
    ]

    subject = f"New Comp-Off Request - {employee.first_name}"

    message = f"""
Employee: {employee.first_name} {employee.last_name}

Worked Date: {compoff.work_date}
Hours Worked: {compoff.hours_worked}

Status: Pending
"""

    send_notification(subject, message, recipients)


def compoff_status_email(compoff, approver, action):

    employee = compoff.employee

    recipients = [
        employee.email,
        employee.pa.email if employee.pa else None,
        employee.sa.email if employee.sa else None,
        employee.hr.email if employee.hr else None,
    ]

    subject = f"Comp-Off {action} - {employee.first_name}"

    message = f"""
Comp-Off {action}

Employee: {employee.first_name} {employee.last_name}
Worked Date: {compoff.work_date}
Hours Worked: {compoff.hours_worked}

Action By: {approver.first_name}
Status: {compoff.status}
"""

    send_notification(subject, message, recipients)



def send_compoff_edited_email(compoff, employee, old_date, old_hours):

    recipients = set()

    # Employee
    if employee.email:
        recipients.add(employee.email)

    # Reporting managers
    if employee.pa and employee.pa.email:
        recipients.add(employee.pa.email)

    if employee.sa and employee.sa.email:
        recipients.add(employee.sa.email)

    if employee.hr and employee.hr.email:
        recipients.add(employee.hr.email)

    subject = f"Comp-Off Updated | {employee.emp_code}"

    message = f"""
Comp-Off Request Updated

Employee: {employee.first_name} {employee.last_name}
Employee ID: {employee.emp_code}

Previous Details
Work Date: {old_date}
Hours Worked: {old_hours}

Updated Details
Work Date: {compoff.work_date}
Hours Worked: {compoff.hours_worked}

Please review if necessary.

LeaveLedger System
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        list(recipients),
        fail_silently=False
    )