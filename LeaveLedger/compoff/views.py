from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now

from .models import CompOff, CompOffApproval
from leave.models import LeaveBalance
from audit.utils import log_action
from accounts.models import Employee
from notifications.email_service import (
    compoff_applied_email,
    compoff_status_email
)

@login_required
def apply_compoff(request):

    actor = request.user.employee_profile
    is_hr = actor.role == "HR"

    # -------------------------------------------------
    # RESOLVE TARGET EMPLOYEE
    # -------------------------------------------------
    employee_id = request.POST.get("employee_id") or request.GET.get("employee_id")

    if is_hr and employee_id:
        employee = get_object_or_404(Employee, employee_id=employee_id)
        is_hr_override = True
    else:
        employee = actor
        is_hr_override = False

    current_year = now().year

    compoffs = CompOff.objects.filter(
        employee=employee
    ).prefetch_related("approvals").order_by("-created_at")

    # -------------------------------------------------
    # APPLY COMPOFF
    # -------------------------------------------------
    if request.method == "POST":
        work_date = request.POST.get("worked_date")
        hours_worked = request.POST.get("hours_worked")

        if not work_date:
            messages.error(request, "Worked date is required.")
            return redirect(request.path)

        try:
            hours_worked = int(hours_worked)
        except (TypeError, ValueError):
            messages.error(request, "Invalid hours worked.")
            return redirect(request.path)

        if hours_worked < 8:
            messages.error(request, "Minimum 8 hours required.")
            return redirect(request.path)
        
        existing = CompOff.objects.filter(
            employee=employee,
            work_date=work_date,
        ).exclude(status="Cancelled")

        if existing.exists():
            messages.error(
                request,
                "Comp-Off already applied for this date."
            )
            return redirect(request.path)

        # -------------------------------------------------
        # CREATE COMPOFF REQUEST
        # -------------------------------------------------
        compoff = CompOff.objects.create(
            employee=employee,
            work_date=work_date,
            hours_worked=hours_worked,
            year=current_year,
            status="Approved" if is_hr_override else "Pending"
        )

        # -------------------------------------------------
        # HR OVERRIDE FLOW
        # -------------------------------------------------
        if is_hr_override:

            # Update balance immediately
            balance, _ = LeaveBalance.objects.get_or_create(
                employee=employee,
                year=current_year
            )

            balance.compoff_credit += 1
            balance.save()

            # Create approval record so history shows entry
            CompOffApproval.objects.create(
                compoff=compoff,
                approver=actor,
                approver_role="HR",
                status="Approved"
            )

        # -------------------------------------------------
        # NORMAL EMPLOYEE FLOW
        # -------------------------------------------------
        else:
            approvers = []

            if employee.pa:
                approvers.append((employee.pa, "RM1"))

            if employee.sa and employee.sa not in [a[0] for a in approvers]:
                approvers.append((employee.sa, "RM2"))

            if employee.hr and employee.hr not in [a[0] for a in approvers]:
                approvers.append((employee.hr, "HR"))

            for approver, role in approvers:
                CompOffApproval.objects.create(
                    compoff=compoff,
                    approver=approver,
                    approver_role=role,
                    status="Pending"
                )

        # -------------------------------------------------
        # AUDIT LOG
        # -------------------------------------------------
        log_action(
            actor=actor if is_hr_override else employee,
            module="COMPOFF",
            action=(
                f"HR applied CompOff for {employee.emp_code} ({work_date})"
                if is_hr_override
                else f"Applied CompOff for {work_date}"
            )
        )
        compoff_applied_email(compoff)

        # -------------------------------------------------
        # REDIRECT
        # -------------------------------------------------
        if is_hr_override:
            return redirect("employee_detail", employee_id=employee.employee_id)

        return redirect("apply_compoff")

    # -------------------------------------------------
    # RENDER PAGE
    # -------------------------------------------------
    return render(
        request,
        "compoff/apply_compoff.html",
        {
            "compoffs": compoffs,
            "employee": employee,
            "is_hr_override": is_hr_override
        }
    )
@login_required
@login_required
def approve_compoff(request, approval_id):
    approval = get_object_or_404(
        CompOffApproval,
        approval_id=approval_id,
        approver=request.user.employee_profile,

        status="Pending"
    )

    approval.status = "Approved"
    approval.action_date = now()
    approval.save()

    compoff = approval.compoff

    # FINALIZE ONLY IF ALL APPROVED
    if not compoff.approvals.filter(status="Pending").exists():
        compoff.status = "Approved"
        compoff.save()

        balance, _ = LeaveBalance.objects.get_or_create(
            employee=compoff.employee,
            year=compoff.year
        )
        credits = compoff.hours_worked // 8
        balance.compoff_credit += credits

        balance.save()


        log_action(
            actor=approval.approver,
            module="COMPOFF",
            action=f"Final approval for CompOff {compoff.compoff_id}"
        )
        compoff_status_email(compoff, approval.approver, "Approved")


    return redirect("my_compoff_approvals")  # ✅ FIX



@login_required
def reject_compoff(request, approval_id):
    approval = get_object_or_404(
        CompOffApproval,
        approval_id=approval_id,
        approver=request.user.employee_profile,

        status="Pending"
    )

    remarks = request.POST.get("remarks", "").strip()

    approval.status = "Rejected"
    approval.remarks = remarks
    approval.action_date = now()
    approval.save()

    compoff = approval.compoff
    compoff.status = "Rejected"
    compoff.save()

    log_action(
        actor=approval.approver,
        module="COMPOFF",
        action=f"Rejected CompOff {compoff.compoff_id} | {remarks}"
    )
    compoff_status_email(compoff, approval.approver, "Rejected")

    return redirect("my_compoff_approvals")  # ✅ FIX

@login_required
def cancel_compoff(request, compoff_id):
    employee = request.user.employee_profile

    compoff = get_object_or_404(
        CompOff,
        compoff_id=compoff_id,
        employee=employee
    )

    if compoff.status != "Pending":
        messages.error(request, "This Comp-Off request cannot be cancelled.")
        return redirect("apply_compoff")

    compoff.status = "Cancelled"
    compoff.save(update_fields=["status"])

    compoff.approvals.filter(status="Pending").update(status="Cancelled")

    log_action(
        actor=employee,
        module="COMPOFF",
        action=f"Cancelled Comp-Off {compoff.compoff_id}"
    )
    compoff_status_email(compoff, employee, "Cancelled")
    return redirect("apply_compoff")

@login_required
def my_compoff_approvals(request):
    employee = request.user.employee_profile


    status_filter = request.GET.get("status", "Pending")

    approvals = CompOffApproval.objects.filter(
        approver=employee
    ).select_related(
        "compoff",
        "compoff__employee"
    ).order_by("-action_date", "-approval_id")

    if status_filter != "ALL":
        approvals = approvals.filter(status=status_filter)

    context = {
        "approvals": approvals,
        "current_status": status_filter,
        "status_choices": [
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected"),
            ("ALL", "All"),
        ],
    }

    return render(
        request,
        "compoff/my_compoff_approvals.html",
        context
    )
from datetime import date

@login_required
def edit_compoff(request, compoff_id):
    employee = request.user.employee_profile

    compoff = get_object_or_404(
        CompOff,
        compoff_id=compoff_id,
        employee=employee
    )

    # Only pending requests can be edited
    if compoff.status != "Pending":
        return redirect("apply_compoff")

    if request.method == "POST":
        work_date_str = request.POST.get("worked_date")
        hours_worked = request.POST.get("hours_worked")

        if not work_date_str:
            return redirect("edit_compoff", compoff_id=compoff_id)

        try:
            work_date = date.fromisoformat(work_date_str)
        except ValueError:
            return redirect("edit_compoff", compoff_id=compoff_id)

        try:
            hours_worked = int(hours_worked)
        except (TypeError, ValueError):
            return redirect("edit_compoff", compoff_id=compoff_id)

        if hours_worked < 8:
            return redirect("edit_compoff", compoff_id=compoff_id)

        # ✅ Update safely
        # Store old values for email
        old_date = compoff.work_date
        old_hours = compoff.hours_worked

# Update values
        compoff.work_date = work_date
        compoff.hours_worked = hours_worked
        compoff.year = work_date.year
        compoff.save()

        log_action(
            actor=employee,
            module="COMPOFF",
            action=f"Edited Comp-Off {compoff.compoff_id}"
        )
        from notifications.email_service import send_compoff_edited_email

        send_compoff_edited_email(
            compoff=compoff,
            employee=employee,
            old_date=old_date,
            old_hours=old_hours
            )
        return redirect("apply_compoff")

    return render(
        request,
        "compoff/edit_compoff.html",
        {"compoff": compoff}
    )