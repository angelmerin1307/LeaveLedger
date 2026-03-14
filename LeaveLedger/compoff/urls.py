from django.urls import path
from . import views

urlpatterns = [
    path("", views.apply_compoff, name="apply_compoff"),

    path(
        "approvals/",
        views.my_compoff_approvals,
        name="my_compoff_approvals"
    ),

    path(
        "approve/<int:approval_id>/",
        views.approve_compoff,
        name="approve_compoff"
    ),

    path(
        "reject/<int:approval_id>/",
        views.reject_compoff,
        name="reject_compoff"
    ),

    path(
        "cancel/<int:compoff_id>/",
        views.cancel_compoff,
        name="cancel_compoff"
    ),
    path("approvals/", views.my_compoff_approvals, name="my_compoff_approvals"),
    path("approve/<int:approval_id>/", views.approve_compoff, name="approve_compoff"),
    path("reject/<int:approval_id>/", views.reject_compoff, name="reject_compoff"),
    path(
    "edit/<int:compoff_id>/",
    views.edit_compoff,
    name="edit_compoff"
),


]
