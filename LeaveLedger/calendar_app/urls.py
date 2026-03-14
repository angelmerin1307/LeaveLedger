from django.urls import path
from .views import manage_holidays, delete_holiday, edit_holiday

urlpatterns = [
    path("holidays/", manage_holidays, name="manage_holidays"), 
    path("holidays/delete/<int:holiday_id>/", delete_holiday, name="delete_holiday"),
    path("holidays/<int:holiday_id>/edit/", edit_holiday, name="edit_holiday"),
]