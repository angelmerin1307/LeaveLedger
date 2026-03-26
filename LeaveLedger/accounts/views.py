from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.timezone import now
from django.contrib.auth.models import User

from django.db.models import Sum, Count
from django.db.models.functions import ExtractMonth
import json
from datetime import datetime, timedelta
import random
import string
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string

from .forms import EmployeeEditForm
import calendar
from django.db.models import F

from leave.models import LeaveApplication, LeaveBalance, LeaveApproval
from notifications.models import Notification
from payroll.models import Payslip
from audit.models import AuditLog

from .forms import HRCreateEmployeeForm
from django.core.mail import send_mail
from django.conf import settings
import traceback
from django.utils.timezone import now
from compoff.models import CompOff
from accounts.models import Employee
from leave.views import apply_leave
from audit.utils import log_action


# --------------------------------------------------
# POST LOGIN REDIRECT
# --------------------------------------------------
@login_required
def post_login_redirect(request):

    if request.user.is_superuser:
        return redirect("/admin/")

    if not hasattr(request.user, "employee_profile"):
        return redirect("/admin/")

    employee = request.user.employee_profile

    if employee.role == "HR":
        return redirect("employee_dashboard")

    return redirect("employee_dashboard")


current_year = now().year

# --------------------------------------------------
# EMPLOYEE DASHBOARD
# --------------------------------------------------
# --------------------------------------------------
# EMPLOYEE DASHBOARD
# --------------------------------------------------
# --------------------------------------------------
# EMPLOYEE DASHBOARD
# --------------------------------------------------
# --------------------------------------------------
# EMPLOYEE DASHBOARD
# --------------------------------------------------
@login_required
def employee_dashboard(request):
    request.session["active_panel"] = "employee"

    employee = request.user.employee_profile
    selected_year = int(request.GET.get("year", now().year))

    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        year=selected_year
    )

    # -------------------------------
    # Recent Leaves
    # -------------------------------
    leaves = LeaveApplication.objects.filter(
        employee=employee
    ).order_by("-applied_date")[:5]

    # -------------------------------
    # Counts (All Time)
    # -------------------------------
    total_applied = LeaveApplication.objects.filter(employee=employee).count()
    total_approved = LeaveApplication.objects.filter(employee=employee, status="Approved").count()
    total_pending = LeaveApplication.objects.filter(employee=employee, status="Pending").count()
    total_rejected = LeaveApplication.objects.filter(employee=employee, status="Rejected").count()
    total_cancelled = LeaveApplication.objects.filter(employee=employee, status="Cancelled").count()

    # -------------------------------
    # Total Days Used (Selected Year Only)
    # -------------------------------
    total_days_used = (
        LeaveApplication.objects
        .filter(
            employee=employee,
            status="Approved",
            start_date__year=selected_year
        )
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    # -------------------------------
    # Leave Usage by Type (Selected Year)
    # -------------------------------
    leave_type_usage = (
        LeaveApplication.objects
        .filter(
            employee=employee,
            status="Approved",
            start_date__year=selected_year
        )
        .values("leave_type__leave_name")
        .annotate(total=Sum("total_days"))
    )

    cl_used = ml_used = ol_used = comp_used = lop_used = 0

    for item in leave_type_usage:
        name = item["leave_type__leave_name"].lower()
        total = float(item["total"])

        if "casual" in name:
            cl_used = total
        elif "medical" in name:
            ml_used = total
        elif "optional" in name:
            ol_used = total
        elif "comp" in name:
            comp_used = total
        else:
            lop_used = total

    # -------------------------------
    # Monthly Trend BY LEAVE TYPE
    # -------------------------------
    monthly_data = (
        LeaveApplication.objects
        .filter(
            employee=employee,
            status="Approved",
            start_date__year=selected_year
        )
        .annotate(month=ExtractMonth("start_date"))
        .values("month", "leave_type__leave_name")
        .annotate(total=Sum("total_days"))
    )

    cl_monthly = [0] * 12
    ml_monthly = [0] * 12
    ol_monthly = [0] * 12
    comp_monthly = [0] * 12
    lop_monthly = [0] * 12

    for item in monthly_data:
        month_index = item["month"] - 1
        name = item["leave_type__leave_name"].lower()
        total = float(item["total"])

        if "casual" in name:
            cl_monthly[month_index] += total
        elif "medical" in name:
            ml_monthly[month_index] += total
        elif "optional" in name:
            ol_monthly[month_index] += total
        elif "comp" in name:
            comp_monthly[month_index] += total
        else:
            lop_monthly[month_index] += total

    return render(
        request,
        "dashboards/employee.html",
        {
            "employee": employee,
            "balance": balance,
            "leaves": leaves,
            "total_applied": total_applied,
            "total_approved": total_approved,
            "total_pending": total_pending,
            "total_rejected": total_rejected,
            "total_cancelled": total_cancelled,
            "total_days_used": total_days_used,
            "lop_taken": balance.lop_taken,

            "selected_year": selected_year,
            "year_range": range(now().year - 3, now().year + 2),

            "cl_used": cl_used,
            "ml_used": ml_used,
            "ol_used": ol_used,
            "comp_used": comp_used,
            "lop_used": lop_used,

            "cl_monthly": cl_monthly,
            "ml_monthly": ml_monthly,
            "ol_monthly": ol_monthly,
            "comp_monthly": comp_monthly,
            "lop_monthly": lop_monthly,
        }
    )
@login_required
def my_profile(request):
    employee = request.user.employee_profile

    year = now().year

    leave_balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        year=year
    )

    return render(
        request,
        "accounts/my_profile.html",
        {
            "employee": employee,
            "leave_balance": leave_balance,
        }
    )



@login_required
def hr_dashboard(request):

    request.session["active_panel"] = "hr"

    if request.user.is_superuser:
        return redirect("/admin/")

    if not hasattr(request.user, "employee_profile"):
        return redirect("employee_dashboard")

    hr = request.user.employee_profile
    if hr.role != "HR":
        return redirect("employee_dashboard")

    today = now().date()
    current_year = today.year

    # ==================================================
    # 1️⃣ ORGANIZATION SNAPSHOT
    # ==================================================
    total_employees = Employee.objects.filter(is_active=True).count()

    today_leave_qs = LeaveApplication.objects.filter(
        status="Approved",
        start_date__lte=today,
        end_date__gte=today
    )

    today_on_leave = today_leave_qs.count()
    present_today = total_employees - today_on_leave

    attendance_percentage = 0
    if total_employees:
        attendance_percentage = round(
            (present_today / total_employees) * 100, 1
        )

    # ==================================================
    # 2️⃣ KPI COUNTS
    # ==================================================
    pending_leaves = LeaveApplication.objects.filter(
        status="Pending"
    ).select_related("employee", "leave_type")

    pending_compoffs = CompOff.objects.filter(
        status="Pending"
    ).select_related("employee")

    # ==================================================
    # 3️⃣ WORKFORCE METRICS (YTD)
    # ==================================================
    total_leave_days_ytd = (
        LeaveApplication.objects
        .filter(status="Approved", start_date__year=current_year)
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    avg_leave_per_employee = 0
    if total_employees:
        avg_leave_per_employee = round(
            total_leave_days_ytd / total_employees, 2
        )

    leave_utilization_percentage = 0
    theoretical_capacity = total_employees * 365
    if theoretical_capacity:
        leave_utilization_percentage = round(
            (total_leave_days_ytd / theoretical_capacity) * 100, 2
        )

    # ==================================================
    # 4️⃣ LEAVE DISTRIBUTION (ORG LEVEL - FIXED ORDER)
    # ==================================================
    approved_leaves = LeaveApplication.objects.filter(
        status="Approved",
        start_date__year=current_year
    )

    cl_used = (
        approved_leaves
        .filter(leave_type__leave_name__icontains="casual")
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    ml_used = (
        approved_leaves
        .filter(leave_type__leave_name__icontains="medical")
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    ol_used = (
        approved_leaves
        .filter(leave_type__leave_name__icontains="optional")
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    comp_used = (
        approved_leaves
        .filter(leave_type__leave_name__icontains="comp")
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    lop_used = (
        approved_leaves
        .filter(leave_type__leave_name__icontains="lop")
        .aggregate(total=Sum("total_days"))["total"] or 0
    )

    leave_labels = ["CL", "ML", "OL", "Comp-Off", "LOP"]

    leave_values = [
        float(cl_used),
        float(ml_used),
        float(ol_used),
        float(comp_used),
        float(lop_used)
    ]

    # ==================================================
    # 5️⃣ MONTHLY TREND
    # ==================================================
    monthly_data = (
        LeaveApplication.objects
        .filter(status="Approved", start_date__year=current_year)
        .annotate(month=ExtractMonth("start_date"))
        .values("month")
        .annotate(total=Sum("total_days"))
    )

    monthly_totals = [0] * 12
    for item in monthly_data:
        monthly_totals[item["month"] - 1] = float(item["total"])

    # ==================================================
    # 6️⃣ RISK INDICATORS
    # ==================================================
    low_balance_employees = LeaveBalance.objects.filter(
        year=current_year,
        cl_balance__lt=3
    ).select_related("employee")[:5]

    high_frequency_users = (
        LeaveApplication.objects
        .filter(status="Approved", start_date__year=current_year)
        .values("employee__first_name")
        .annotate(total_leaves=Count("leave_id"))
        .filter(total_leaves__gte=5)
        .order_by("-total_leaves")[:5]
    )

    upcoming_long_leaves = LeaveApplication.objects.filter(
        status="Approved",
        start_date__gt=today,
        total_days__gte=5
    ).select_related("employee", "leave_type")[:5]

    excessive_lop_users = (
        LeaveApplication.objects
        .filter(
            status="Approved",
            start_date__year=current_year,
            leave_type__leave_name__icontains="lop"
        )
        .values("employee__first_name")
        .annotate(total_days=Sum("total_days"))
        .filter(total_days__gte=5)
        .order_by("-total_days")[:5]
    )

    # ==================================================
    # 7️⃣ MONTHLY BREAKDOWN BY TYPE
    # ==================================================
    leave_types = LeaveApplication.objects.values_list(
        "leave_type__leave_name", flat=True
    ).distinct()

    type_monthly_data = {}

    for leave_type in leave_types:
        monthly_array = [0] * 12

        monthly_qs = (
            LeaveApplication.objects
            .filter(
                status="Approved",
                start_date__year=current_year,
                leave_type__leave_name=leave_type
            )
            .annotate(month=ExtractMonth("start_date"))
            .values("month")
            .annotate(total=Sum("total_days"))
        )

        for item in monthly_qs:
            monthly_array[item["month"] - 1] = float(item["total"])

        type_monthly_data[leave_type] = monthly_array

    # ==================================================
    # 8️⃣ MONTHLY ATTENDANCE CALCULATION
    # ==================================================
    attendance_monthly = []

    for month in range(1, 13):

        month_days = calendar.monthrange(current_year, month)[1]

        leave_days = (
            LeaveApplication.objects
            .filter(
                status="Approved",
                start_date__year=current_year,
                start_date__month=month
            )
            .aggregate(total=Sum("total_days"))["total"] or 0
        )

        capacity = total_employees * month_days

        if capacity > 0:
            attendance_rate = round(
                float(1 - (float(leave_days) / float(capacity))) * 100,
                2
            )
        else:
            attendance_rate = 100

        attendance_monthly.append(float(attendance_rate))

    # ==================================================
    # 9️⃣ LEAVE LOAD INDEX
    # ==================================================
    leave_load_index = leave_utilization_percentage

    return render(
        request,
        "dashboards/hr.html",
        {
            # Snapshot
            "total_employees": total_employees,
            "today_on_leave": today_on_leave,
            "present_today": present_today,
            "attendance_percentage": attendance_percentage,

            # KPIs
            "pending_leave_count": pending_leaves.count(),
            "pending_compoff_count": pending_compoffs.count(),
            "pending_leaves": pending_leaves[:5],
            "pending_compoffs": pending_compoffs[:5],

            # Workforce metrics
            "avg_leave_per_employee": avg_leave_per_employee,
            "leave_utilization_percentage": leave_utilization_percentage,
            "leave_load_index": leave_load_index,

            # Analytics
            "cl_used": cl_used,
            "ml_used": ml_used,
            "ol_used": ol_used,
            "comp_used": comp_used,
            "lop_used": lop_used,
            "leave_labels": json.dumps(leave_labels),
            "leave_values": json.dumps(leave_values),
            "monthly_totals": json.dumps(monthly_totals),
            "type_monthly_data": json.dumps(type_monthly_data),
            "attendance_monthly": json.dumps(attendance_monthly),

            # Risk
            "low_balance_employees": low_balance_employees,
            "high_frequency_users": high_frequency_users,
            "upcoming_long_leaves": upcoming_long_leaves,
            "excessive_lop_users": excessive_lop_users,
        }
    )

@login_required
def hr_create_employee(request):
    hr = request.user.employee_profile

    if hr.role != "HR":
        return redirect("employee_dashboard")

    if request.method == "POST":
        form = HRCreateEmployeeForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():

                    employee = form.save(commit=False)
                    username = employee.emp_code.lower()

                    # Check username exists
                    if User.objects.filter(username=username).exists():
                        messages.error(request, "Employee code already exists.")
                        return redirect("hr_create_employee")

                    # Generate temporary password
                    temp_password = get_random_string(10)

                    # Create Django auth user
                    user = User.objects.create_user(
                        username=username,
                        password=temp_password,
                        email=employee.email,
                    )

                    # Link employee to user
                    employee.user = user
                    employee.role = "EMPLOYEE"
                    employee.save()

                    # Audit log
                    try:
                        AuditLog.objects.create(
                            user=hr,
                            module="EMPLOYEE",
                            action=f"Created employee {employee.emp_code}",
                        )
                    except Exception as e:
                        print("Audit log failed:", e)

                # Send email (outside transaction)
                try:
                    send_mail(
                        subject="Your LeaveLedger Login Credentials",
                        message=(
                            "Hello,\n\n"
                            "Your LeaveLedger account has been created.\n\n"
                            f"Username: {username}\n"
                            f"Temporary Password: {temp_password}\n\n"
                            "Please login and change your password."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[employee.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print("Email failed:", e)

                messages.success(request, "Employee created successfully.")
                return redirect("manage_employees")

            except IntegrityError:
                messages.error(
                    request,
                    "Duplicate data detected (Email / Phone / PAN / UAN / Account already exists)."
                )
                return redirect("hr_create_employee")

            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Error creating employee: {str(e)}")
                return redirect("hr_create_employee")

    else:
        form = HRCreateEmployeeForm()

    return render(request, "hr/create_employee.html", {"form": form})
@login_required
def manage_employees(request):

    # Safety checks
    if request.user.is_superuser:
        return redirect("/admin/")

    if not hasattr(request.user, "employee_profile"):
        return redirect("/admin/")

    hr = request.user.employee_profile

    if hr.role != "HR":
        return redirect("employee_dashboard")

    # Fetch all employees
    employees = Employee.objects.all().order_by("emp_code")

    return render(
        request,
        "hr/employee_list.html",
        {"employees": employees}
    )

@login_required
def employee_detail(request, employee_id=None):
    viewer = request.user.employee_profile

    # -------------------------------------------------
    # RESOLVE EMPLOYEE BEING VIEWED
    # -------------------------------------------------
    if employee_id:
        employee = get_object_or_404(Employee, employee_id=employee_id)

        # Non-HR cannot view other profiles
        if viewer.role != "HR" and viewer != employee:
            return redirect("employee_dashboard")
    else:
        employee = viewer

    is_hr_view = viewer.role == "HR"
    is_self_view = viewer == employee

    year = now().year

   

    # -------------------------------------------------
    # LEAVE BALANCE
    # -------------------------------------------------
    leave_balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        year=year
    )

    # -------------------------------------------------
    # BASE CONTEXT (ALWAYS AVAILABLE)
    # -------------------------------------------------
    context = {
        "employee": employee,
        "leave_balance": leave_balance,
        "lop_count": leave_balance.lop_taken,
        "is_hr_view": is_hr_view,
        "is_self_view": is_self_view,
    }

    # -------------------------------------------------
    # HR ADDITIONAL DATA
    # -------------------------------------------------
    if is_hr_view:

        recent_leaves = LeaveApplication.objects.filter(
            employee=employee
        ).order_by("-applied_date")[:5]

        recent_compoffs = CompOff.objects.filter(
            employee=employee
        ).order_by("-work_date")[:5]

        total_leaves_applied = LeaveApplication.objects.filter(
            employee=employee
        ).count()

        total_leaves_approved = LeaveApplication.objects.filter(
            employee=employee,
            status="Approved"
        ).count()

        total_leaves_rejected = LeaveApplication.objects.filter(
            employee=employee,
            status="Rejected"
        ).count()

        total_leaves_pending = LeaveApplication.objects.filter(
            employee=employee,
            status="Pending"
        ).count()

        total_days_approved = LeaveApplication.objects.filter(
            employee=employee,
            status="Approved"
        ).aggregate(Sum("total_days"))["total_days__sum"] or 0

        total_cancelled = LeaveApplication.objects.filter(employee=employee, status="Cancelled").count()

        context.update({
            "recent_leaves": recent_leaves,
            "recent_compoffs": recent_compoffs,
            "total_leaves_applied": total_leaves_applied,
            "total_leaves_approved": total_leaves_approved,
            "total_leaves_rejected": total_leaves_rejected,
            "total_leaves_pending": total_leaves_pending,
            "total_days_approved": total_days_approved,
            "total_cancelled": total_cancelled,
        })

    # -------------------------------------------------
    # RENDER
    # -------------------------------------------------
    return render(
        request,
        "hr/employee_detail.html",
        context
    )

@login_required
def employee_edit(request, employee_id):

    # Safety checks
    if request.user.is_superuser:
        return redirect("/admin/")

    if not hasattr(request.user, "employee_profile"):
        return redirect("/admin/")

    hr = request.user.employee_profile
    if hr.role != "HR":
        return redirect("employee_dashboard")

    employee = get_object_or_404(Employee, employee_id=employee_id)

    if request.method == "POST":
        form = EmployeeEditForm(request.POST, instance=employee)

        if form.is_valid():
            form.save()

            # 🔒 AUDIT LOG
            AuditLog.objects.create(
                user=hr,
                module="EMPLOYEE",
                action=f"Edited employee profile: {employee.emp_code}"
            )

            messages.success(request, "Employee profile updated successfully.")
            return redirect("employee_detail", employee_id=employee.employee_id)

    else:
        form = EmployeeEditForm(instance=employee)

    return render(
        request,
        "hr/employee_edit.html",
        {
            "employee": employee,
            "form": form
        }
    )

@login_required
def hr_apply_leave(request, employee_id):
    hr = request.user.employee_profile

    if hr.role != "HR":
        messages.error(request, "Access denied.")
        return redirect("employee_dashboard")

    return redirect(
        f"{reverse('apply_leave')}?employee_id={employee_id}"
    )



#FWLRyA05sN  WEpeMUAwl3