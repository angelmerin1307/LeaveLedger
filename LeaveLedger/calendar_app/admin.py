from django.contrib import admin
from .models import Holiday

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('holiday_date', 'holiday_name', 'holiday_type')
    list_filter = ('holiday_type',)
    ordering = ('holiday_date',)
