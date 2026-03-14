from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.core.paginator import Paginator

from .models import AuditLog


@login_required
def audit_log_list(request):
    user = request.user

    # -------------------------------
    # SAFETY CHECKS
    # -------------------------------
    if user.is_superuser:
        return redirect("/admin/")

    if not hasattr(user, "employee_profile"):
        return redirect("/admin/")

    employee = user.employee_profile

    # HR-only access
    if employee.role != "HR":
        return redirect("employee_dashboard")

    # -------------------------------
    # FILTERS
    # -------------------------------
    action = request.GET.get("action")
    module = request.GET.get("module")
    emp_code = request.GET.get("user")

    logs = (
        AuditLog.objects
        .select_related("user")
        .order_by("-timestamp")
    )

    if action:
        logs = logs.filter(action__icontains=action)

    if module:
        logs = logs.filter(module__icontains=module)

    if emp_code:
        logs = logs.filter(user__emp_code__icontains=emp_code)

    # -------------------------------
    # PAGINATION
    # -------------------------------
    paginator = Paginator(logs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "action": action or "",
        "module": module or "",
        "user_filter": emp_code or "",
    }

    return render(request, "audit/audit_logs.html", context,)
