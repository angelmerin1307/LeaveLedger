from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.db.models import Q
from django.db.models import Sum

from accounts.models import Employee
from .models import LeaveApplication, LeaveBalance, LeaveType, LeaveApproval
from compoff.models import CompOff
from audit.utils import log_action
from datetime import timedelta
from calendar import monthrange
from decimal import Decimal
from notifications.email_service import (
    leave_applied_email,
    leave_edited_email,
    leave_cancelled_email,
    leave_status_email
)


from calendar_app.models import Holiday
from decimal import Decimal
from datetime import date, timedelta
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required


@login_required
def apply_leave(request):
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

    year = now().year

    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        year=year
    )

    ui_holidays = list(
        Holiday.objects.filter(
            holiday_date__year=year
        ).values("holiday_date", "holiday_type",)
    )

    formatted_holidays = [
        {
            "date": h["holiday_date"].isoformat(),
            "type": h["holiday_type"]
        }
        for h in ui_holidays
    ]

    leave_types = LeaveType.objects.all()

    if balance.ol_balance <= 0:
        leave_types = leave_types.exclude(
            leave_name__icontains="optional"
        )

    # =================================================
    # POST REQUEST
    # =================================================
    if request.method == "POST":

        leave_type_id = request.POST.get("leave_type")
        edit_leave_id = request.POST.get("edit_leave_id")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")
        half_day = request.POST.get("half_day")

        # -----------------------
        # Basic Validation
        # -----------------------
        if not leave_type_id or not start_date or not end_date:
            return render(request, "leave/apply_leave.html", {
                "employee": employee,
                "leave_types": leave_types,
                "balance": balance,
                "compoff_credits": balance.compoff_credit,
                "ui_holidays": formatted_holidays,
                "is_hr_override": is_hr_override,
                "error": "All fields are required."
            })

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        if end < start:
            return render(request, "leave/apply_leave.html", {
                "employee": employee,
                "leave_types": leave_types,
                "balance": balance,
                "compoff_credits": balance.compoff_credit,
                "ui_holidays": formatted_holidays,
                "is_hr_override": is_hr_override,
                "error": "End date cannot be before start date."
            })

        leave_type = get_object_or_404(LeaveType, pk=leave_type_id)

        # -----------------------
        # HALF DAY LOGIC
        # -----------------------
        if half_day:
            if start != end:
                return render(request, "leave/apply_leave.html", {
                    "employee": employee,
                    "leave_types": leave_types,
                    "balance": balance,
                    "compoff_credits": balance.compoff_credit,
                    "ui_holidays": formatted_holidays,
                    "is_hr_override": is_hr_override,
                    "error": "Half day allowed only for single-day leave."
                })

            total_days = Decimal("0.5")

        else:
            # -----------------------
            # HOLIDAY CHECK
            # -----------------------
            holidays = Holiday.objects.filter(
                holiday_date__range=[start, end]
            )
            holiday_map = {h.holiday_date: h.holiday_type for h in holidays}

            total_days = Decimal("0.0")
            current = start

            while current <= end:
                holiday_type = holiday_map.get(current)

                if leave_type.leave_name == "Optional Leave":
                    if holiday_type == Holiday.HolidayType.OPTIONAL:
                        total_days += Decimal("1.0")
                else:
                    if holiday_type is None:
                        total_days += Decimal("1.0")

                current += timedelta(days=1)

        if total_days <= 0:
            return render(request, "leave/apply_leave.html", {
                "employee": employee,
                "leave_types": leave_types,
                "balance": balance,
                "compoff_credits": balance.compoff_credit,
                "ui_holidays": formatted_holidays,
                "is_hr_override": is_hr_override,
                "error": "No valid leave days selected."
            })

        # -----------------------
        # OVERLAP CHECK
        # -----------------------
        overlap_qs = LeaveApplication.objects.filter(
            employee=employee,
            start_date__lte=end,
            end_date__gte=start
        ).exclude(status__in=["Rejected", "Cancelled"])

        if edit_leave_id:
            overlap_qs = overlap_qs.exclude(leave_id=edit_leave_id)

        if overlap_qs.exists():
            return render(request, "leave/apply_leave.html", {
                "employee": employee,
                "leave_types": leave_types,
                "balance": balance,
                "compoff_credits": balance.compoff_credit,
                "ui_holidays": formatted_holidays,
                "is_hr_override": is_hr_override,
                "error": "Leave already exists for the selected date range."
            })

        # -----------------------
        # BALANCE CHECK
        # -----------------------
        lt = leave_type.leave_name.lower()

        if "casual" in lt:
            available = balance.cl_balance
        elif "medical" in lt:
            available = balance.ml_balance
        elif "optional" in lt:
            available = balance.ol_balance
        elif "compensatory" in lt:
            available = balance.compoff_credit
        else:
            available = None

        # Calculate pending leave of same type
        pending_days = LeaveApplication.objects.filter(
            employee=employee,
            leave_type=leave_type,
            status="Pending"
        ).exclude(
            leave_id=edit_leave_id
        ).aggregate(
            total=Sum("total_days")
        )["total"] or Decimal("0.0")

        effective_available = available - pending_days if available is not None else None

        if effective_available is not None and total_days > effective_available:
            return render(request, "leave/apply_leave.html", {
                "employee": employee,
                "leave_types": leave_types,
                "balance": balance,
                "compoff_credits": balance.compoff_credit,
                "ui_holidays": formatted_holidays,
                "is_hr_override": is_hr_override,
                "error": f"Insufficient balance. Available to apply: {effective_available}"
            })

        # =================================================
        # CREATE OR UPDATE
        # =================================================
        if edit_leave_id:
            leave = get_object_or_404(
                LeaveApplication,
                leave_id=edit_leave_id,
                employee=employee
            )

            old_start = leave.start_date
            old_end = leave.end_date
            old_type = leave.leave_type.leave_name

            leave.leave_type = leave_type
            leave.start_date = start
            leave.end_date = end
            leave.total_days = total_days
            leave.reason = reason
            leave.status = "Pending"
            leave.save()

            leave.approvals.all().delete()

            log_action(
                actor=employee,
                module="LEAVE",
                action=(
                    f"Edited leave {leave.leave_id} | "
                    f"{old_type} ({old_start} → {old_end}) "
                    f"→ {leave_type.leave_name} ({start} → {end})"
                )
            )
            leave_edited_email(leave, old_start, old_end, old_type)
            messages.success(request, "Leave updated successfully.")

        else:
            leave = LeaveApplication.objects.create(
                employee=employee,
                leave_type=leave_type,
                start_date=start,
                end_date=end,
                total_days=total_days,
                reason=reason,
                status="Approved" if is_hr_override else "Pending"
            )

            log_action(
                actor=actor if is_hr_override else employee,
                module="LEAVE",
                action=(
                    f"HR applied leave for {employee.emp_code} ({start} → {end})"
                    if is_hr_override
                    else f"Applied leave ({start} → {end})"
                )
            )
            leave_applied_email(leave)
            messages.success(request, "Leave applied successfully.")

        # =================================================
        # APPROVAL FLOW
        # =================================================
        if is_hr_override:
            deduct_leave_balance(leave)

            LeaveApproval.objects.create(
                leave=leave,
                approver=actor,
                approver_role="HR",
                status="Approved"
            )

            return redirect("employee_detail", employee_id=employee.employee_id)

        else:
            if employee.pa:
                LeaveApproval.objects.create(
                    leave=leave,
                    approver=employee.pa,
                    approver_role="RM1"
                )

            if employee.sa and employee.sa != employee.pa:
                LeaveApproval.objects.create(
                    leave=leave,
                    approver=employee.sa,
                    approver_role="RM2"
                )

            if employee.hr and employee.hr not in {employee.pa, employee.sa}:
                LeaveApproval.objects.create(
                    leave=leave,
                    approver=employee.hr,
                    approver_role="HR"
                )

            return redirect("employee_dashboard")

    # =================================================
    # GET REQUEST
    # =================================================
    return render(request, "leave/apply_leave.html", {
        "employee": employee,
        "leave_types": leave_types,
        "balance": balance,
        "compoff_credits": balance.compoff_credit,
        "ui_holidays": formatted_holidays,
        "is_hr_override": is_hr_override,
    })
# ==================================================
@login_required
def pending_approvals(request):
    employee = request.user.employee_profile

    status_filter = request.GET.get("status", "Pending")

    approvals = LeaveApproval.objects.filter(
        approver=employee
    ).select_related(
        "leave",
        "leave__employee",
        "leave__leave_type"
    ).prefetch_related(
        "leave__approvals__approver"
    )

    if status_filter != "All":
        approvals = approvals.filter(status=status_filter)

    approvals = approvals.order_by("-approval_id")

    return render(
        request,
        "leave/pending_approvals.html",
        {
            "approvals": approvals,
            "current_status": status_filter
        }
    )


# ==================================================
# APPROVE LEAVE (SINGLE APPROVER)
# ==================================================
# ==================================================
# APPROVE LEAVE (SINGLE APPROVER)
# ==================================================
@login_required
def approve_leave(request, approval_id):
    approver = request.user.employee_profile

    approval = LeaveApproval.objects.filter(
        approval_id=approval_id,
        approver=approver,
        status="Pending"
    ).select_related("leave").first()

    if not approval:
        return redirect("pending_approvals")

    leave = approval.leave

    # 🔒 Prevent approving completed leave
    if leave.display_status == "Completed":
        return redirect("pending_approvals")

    # ------------------------------------
    # 1️⃣ APPROVE THIS LEVEL
    # ------------------------------------
    approval.status = "Approved"
    approval.action_date = now()
    approval.save(update_fields=["status", "action_date"])

    # 🔎 AUDIT THIS APPROVAL (LEVEL LOG)
    log_action(
        actor=approver,
        module="LEAVE",
        action=(
            f"{approval.approver_role} approved leave "
            f"{leave.leave_id} for {leave.employee.emp_code}"
        )
    )

    # ------------------------------------
    # 2️⃣ CHECK FINAL STATUS
    # ------------------------------------

    # If any rejection exists → force rejected
    if leave.approvals.filter(status="Rejected").exists():
        leave.status = "Rejected"
        leave.save(update_fields=["status"])

    # If no pending and no rejection → approved
    elif not leave.approvals.filter(status="Pending").exists():
        leave.status = "Approved"
        leave.save(update_fields=["status"])

        deduct_leave_balance(leave)

        # 🔒 FINAL AUDIT
        log_action(
            actor=approver,
            module="LEAVE",
            action=(
                f"Final approval completed for leave "
                f"{leave.leave_id}"
            )
        )
        leave_status_email(leave, approver, "Approved")

    return redirect("pending_approvals")

# ==================================================
# REJECT LEAVE
# ==================================================
@login_required
def reject_leave(request, approval_id):
    approver = request.user.employee_profile

    approval = LeaveApproval.objects.filter(
        approval_id=approval_id,
        approver=approver,
        status="Pending"
    ).select_related("leave").first()

    if not approval:
        messages.warning(request, "This approval is no longer available.")
        return redirect("pending_approvals")

    remarks = request.POST.get("remarks", "").strip()

    approval.status = "Rejected"
    approval.remarks = remarks
    approval.action_date = now()
    approval.save(update_fields=["status", "remarks", "action_date"])

    leave = approval.leave
    leave.status = "Rejected"
    leave.save(update_fields=["status"])

    log_action(
        actor=approver,
        module="LEAVE",
        action=f"Rejected leave {leave.leave_id} | {remarks}"
    )
    leave_status_email(leave, approver, "Rejected")

    messages.success(request, "Leave rejected.")
    return redirect("pending_approvals")


# ==================================================
# BALANCE DEDUCTION (FINAL ONLY)
# ==================================================
def deduct_leave_balance(leave):
    balance = LeaveBalance.objects.get(
        employee=leave.employee,
        year=leave.start_date.year
    )

    days = Decimal(leave.total_days)
    lt = leave.leave_type.leave_name.lower()

    if "casual" in lt:
        balance.cl_balance -= days

    elif "medical" in lt:
        balance.ml_balance -= days

    elif "optional" in lt:
        balance.ol_balance -= days

    elif "compensatory" in lt:
        balance.compoff_credit -= days

    else:
        balance.lop_taken += days

    balance.save()

@login_required
def leave_history(request):
    viewer = request.user.employee_profile
    employee_id = request.GET.get("employee_id")

    # Default → self
    employee = viewer
    is_hr_view = False

    # If HR wants to view someone else
    if employee_id:
        if viewer.role == "HR":
            employee = get_object_or_404(
                Employee,
                employee_id=employee_id
            )
            is_hr_view = True
        else:
            # Non-HR trying to access someone else
            return redirect("employee_dashboard")

    leaves = LeaveApplication.objects.filter(
        employee=employee
    ).prefetch_related("approvals__approver"
    ).order_by("-applied_date")

    return render(
        request,
        "leave/leave_history.html",
        {
            "leaves": leaves,
            "employee": employee,
            "is_hr_view": is_hr_view,
        }
    )




@login_required
def team_calendar(request):
    manager = request.user.employee_profile

    team = Employee.objects.filter(
        Q(pa=manager) | Q(sa=manager) | Q(employee_id=manager.employee_id)
    )

    today = now().date()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    start_of_month = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)

    # Approved leaves for selected month
    leaves = LeaveApplication.objects.filter(
        employee__in=team,
        status="Approved",
        start_date__lte=end_of_month,
        end_date__gte=start_of_month
    ).select_related("employee", "leave_type")

    # 🔥 PERFORMANCE IMPROVEMENT
    leave_map = defaultdict(list)
    for leave in leaves:
        leave_map[leave.employee.pk].append(leave)

    # Generate days list
    days = [date(year, month, d) for d in range(1, last_day + 1)]

    rows = []

    for emp in team:
        emp_leaves = leave_map.get(emp.pk, [])

        row = {
            "employee": emp,
            "cells": []
        }

        for day in days:
            css_class = ""
            label = ""

            for leave in emp_leaves:
                if leave.start_date <= day <= leave.end_date:

                    leave_name = leave.leave_type.leave_name.lower()

                    if "casual" in leave_name:
                        css_class = "leave-cl"
                        label = "CL"
                    elif "medical" in leave_name:
                        css_class = "leave-ml"
                        label = "ML"
                    elif "optional" in leave_name:
                        css_class = "leave-ol"
                        label = "OL"
                    elif "compensatory" in leave_name:
                        css_class = "leave-co"
                        label = "CO"
                    else:
                        css_class = "leave-lop"
                        label = "LOP"

                    break

            row["cells"].append({
                "date": day,
                "css_class": css_class,
                "label": label
            })

        rows.append(row)

    # 🔥 TODAY ATTENDANCE SNAPSHOT
    today_leaves = LeaveApplication.objects.filter(
        employee__in=team,
        status="Approved",
        start_date__lte=today,
        end_date__gte=today
    )

    today_on_leave = today_leaves.count()
    total_employees = team.count()
    today_present = total_employees - today_on_leave

    return render(
        request,
        "leave/team_calendar.html",
        {
            "rows": rows,
            "days": days,
            "month": month,
            "year": year,
            "today": today,
            "today_present": today_present,
            "today_on_leave": today_on_leave,
            "total_employees": total_employees,
        }
    )
from collections import defaultdict

@login_required
def hr_calendar(request):
    hr = request.user.employee_profile

    if hr.role != "HR":
        messages.error(request, "Access denied.")
        return redirect("employee_dashboard")

    employees = Employee.objects.filter(is_active=True)

    today = now().date()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    start_of_month = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)

    leaves = LeaveApplication.objects.filter(
        employee__in=employees,
        status="Approved",
        start_date__lte=end_of_month,
        end_date__gte=start_of_month
    ).select_related("employee", "leave_type")

    # 🔥 PERFORMANCE IMPROVEMENT
    leave_map = defaultdict(list)
    for leave in leaves:
        leave_map[leave.employee.pk].append(leave)

    days = [date(year, month, d) for d in range(1, last_day + 1)]

    rows = []

    for emp in employees:
        emp_leaves = leave_map.get(emp.pk, [])

        row = {
            "employee": emp,
            "cells": []
        }

        for day in days:
            css_class = ""
            label = ""

            for leave in emp_leaves:
                if leave.start_date <= day <= leave.end_date:

                    leave_name = leave.leave_type.leave_name.lower()

                    if "casual" in leave_name:
                        css_class = "leave-cl"
                        label = "CL"
                    elif "medical" in leave_name:
                        css_class = "leave-ml"
                        label = "ML"
                    elif "optional" in leave_name:
                        css_class = "leave-ol"
                        label = "OL"
                    elif "compensatory" in leave_name:
                        css_class = "leave-co"
                        label = "CO"
                    else:
                        css_class = "leave-lop"
                        label = "LOP"

                    break

            row["cells"].append({
                "date": day,
                "css_class": css_class,
                "label": label
            })

        rows.append(row)

    # 🔥 TODAY ATTENDANCE SNAPSHOT
    today_leaves = LeaveApplication.objects.filter(
        employee__in=employees,
        status="Approved",
        start_date__lte=today,
        end_date__gte=today
    )

    today_on_leave = today_leaves.count()
    total_employees = employees.count()
    today_present = total_employees - today_on_leave

    return render(
        request,
        "leave/team_calendar.html",
        {
            "rows": rows,
            "days": days,
            "month": month,
            "year": year,
            "title": "HR Leave Calendar",
            "today": today,
            "today_present": today_present,
            "today_on_leave": today_on_leave,
            "total_employees": total_employees,
        }
    )
@login_required
def cancel_leave(request, leave_id):
    user = request.user.employee_profile

    # -------------------------------
    # Allow HR to cancel any leave
    # -------------------------------
    if user.role == "HR":
        leave = get_object_or_404(
            LeaveApplication,
            leave_id=leave_id
        )
    else:
        leave = get_object_or_404(
            LeaveApplication,
            leave_id=leave_id,
            employee=user
        )

    today = now().date()
    # 🔒 Prevent cancelling completed leave
    if leave.display_status == "Completed":
        return redirect("leave_history")

    # ⛔ Employee cannot cancel past leave
    if user.role != "HR" and leave.start_date < today:
        return redirect("leave_history")

    if leave.status == "Cancelled":
        return redirect("leave_history")

    # --------------------------------
    # Reverse balance only if approved
    # --------------------------------
    if leave.status == "Approved":
        balance = LeaveBalance.objects.get(
            employee=leave.employee,
            year=leave.start_date.year
        )

        days = Decimal(leave.total_days)
        lt = leave.leave_type.leave_name.lower()

        if "casual" in lt:
            balance.cl_balance += days
        elif "medical" in lt:
            balance.ml_balance += days
        elif "optional" in lt:
            balance.ol_balance += days
        elif "compensatory" in lt:
            balance.compoff_credit += days
        else:
            balance.lop_taken = max(balance.lop_taken - days, 0)

        balance.save()

    leave.status = "Cancelled"
    leave.cancelled_by = user
    leave.cancelled_at = now()
    leave.save(update_fields=["status","cancelled_by","cancelled_at"])

    

    log_action(
        actor=user,
        module="LEAVE",
        action=f"Cancelled leave {leave.leave_id}"
    )
    leave_cancelled_email(leave)
    # -------------------------------
    # Redirect logic
    # -------------------------------
    if user.role == "HR":
        return redirect("employee_detail", employee_id=leave.employee.employee_id)

    return redirect("leave_history")

@login_required
def edit_leave(request, leave_id):
    user = request.user.employee_profile

    leave = get_object_or_404(
        LeaveApplication,
        leave_id=leave_id,
        employee=user,
        status="Pending"
    )

    year = leave.start_date.year

    balance = LeaveBalance.objects.get(
        employee=leave.employee,
        year=year
    )

    leave_types = LeaveType.objects.all()

    ui_holidays = list(
        Holiday.objects.filter(
            holiday_date__year=year
        ).values_list("holiday_date", flat=True)
    )

    return render(
        request,
        "leave/apply_leave.html",
        {
            "employee": leave.employee,
            "leave_types": leave_types,
            "balance": balance,
            "compoff_credits": balance.compoff_credit,
            "ui_holidays": [d.isoformat() for d in ui_holidays],
            "edit_leave": leave,  # ⭐ important
            "is_edit_mode": True
        }
    )