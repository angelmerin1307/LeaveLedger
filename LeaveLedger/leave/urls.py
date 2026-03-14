from django.urls import path

from .views import (
    apply_leave,
    leave_history,
    team_calendar,
    hr_calendar, 
    pending_approvals,
    approve_leave,
    reject_leave,
    cancel_leave,
    edit_leave,
)

urlpatterns = [
    path("apply/", apply_leave, name="apply_leave"),
    path("history/", leave_history, name="leave_history"),
    path("team-calendar/", team_calendar, name="team_calendar"),
    path("company-calendar/", hr_calendar, name="hr_calendar"),
    path("pending-approvals/", pending_approvals, name="pending_approvals"),
    path("approve/<int:approval_id>/", approve_leave, name="approve_leave"),
    path("reject/<int:approval_id>/", reject_leave, name="reject_leave"),
    path("cancel/<int:leave_id>/", cancel_leave, name="cancel_leave"),
    path("edit/<int:leave_id>/", edit_leave, name="edit_leave"),


]
