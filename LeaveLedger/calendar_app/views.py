from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.timezone import now
from .models import Holiday
from django.urls import reverse

from audit.utils import log_action



from django.db import IntegrityError


@login_required
def manage_holidays(request):
    employee = request.user.employee_profile

    if employee.role != "HR":
        return redirect("employee_dashboard")

    if request.method == "POST":
        action = request.POST.get("action")

        # ---------------- ADD ----------------
        if action == "add":
            holiday_date = request.POST.get("holiday_date")
            holiday_name = request.POST.get("holiday_name")
            holiday_type = request.POST.get("holiday_type")

            if holiday_date and holiday_name and holiday_type:
                try:
                    holiday = Holiday.objects.create(
                        holiday_date=holiday_date,
                        holiday_name=holiday_name,
                        holiday_type=holiday_type
                    )

                    # SAFE AUDIT LOG
                    try:
                        log_action(
                            actor=employee,
                            module="HOLIDAY",
                            action=f"Added holiday {holiday.holiday_name} ({holiday.holiday_date})"
                        )
                    except Exception as e:
                        print("Audit log failed:", e)

                except IntegrityError:
                    return redirect(reverse("manage_holidays") + "?status=exists")

            return redirect(reverse("manage_holidays") + "?status=added")

        # ---------------- EDIT ----------------
        elif action == "edit":
            holiday_id = request.POST.get("holiday_id")

            h = Holiday.objects.filter(pk=holiday_id).first()
            if h:
                old_date = h.holiday_date
                old_name = h.holiday_name

                h.holiday_date = request.POST.get("holiday_date")
                h.holiday_name = request.POST.get("holiday_name")
                h.holiday_type = request.POST.get("holiday_type")
                h.save()

                try:
                    log_action(
                        actor=employee,
                        module="HOLIDAY",
                        action=f"Updated holiday {old_name} ({old_date}) → {h.holiday_name} ({h.holiday_date})"
                    )
                except Exception as e:
                    print("Audit log failed:", e)

            return redirect(reverse("manage_holidays") + "?status=updated")

        # ---------------- DELETE ----------------
        elif action == "delete":
            holiday_id = request.POST.get("holiday_id")

            h = Holiday.objects.filter(pk=holiday_id).first()
            if h:
                try:
                    log_action(
                        actor=employee,
                        module="HOLIDAY",
                        action=f"Deleted holiday {h.holiday_name} ({h.holiday_date})"
                    )
                except Exception as e:
                    print("Audit log failed:", e)

                h.delete()

            return redirect(reverse("manage_holidays") + "?status=deleted")

    holidays = Holiday.objects.order_by("holiday_date")

    return render(
        request,
        "calendar_app/manage_holidays.html",
        {"holidays": holidays}
    )
@login_required
def delete_holiday(request, holiday_id):
    employee = request.user.employee_profile

    if employee.role != "HR":
        return redirect("employee_dashboard")

    Holiday.objects.filter(pk=holiday_id).delete()
    return redirect("manage_holidays")

@login_required
def edit_holiday(request, holiday_id):
    employee = request.user.employee_profile

    if employee.role != "HR":
        return redirect("employee_dashboard")

    holiday = get_object_or_404(Holiday, pk=holiday_id)

    if request.method == "POST":
        holiday.holiday_date = request.POST["holiday_date"]
        holiday.holiday_name = request.POST["holiday_name"]
        holiday.holiday_type = request.POST["holiday_type"]
        holiday.save()
        return redirect("manage_holidays")

    holidays = Holiday.objects.order_by("holiday_date")

    return render(
        request,
        "calendar_app/manage_holidays.html",
        {
            "holidays": holidays,
            "edit_holiday": holiday,  # 👈 KEY LINE
        }
    )
