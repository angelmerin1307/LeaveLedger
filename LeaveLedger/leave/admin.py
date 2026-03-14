from django.contrib import admin
from .models import LeaveType, LeaveApplication, LeaveApproval, LeaveBalance

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('leave_name', 'is_paid', 'max_per_year')


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'leave_id',
        'employee',
        'leave_type',
        'start_date',
        'end_date',
        'total_days',
        'status',
        'is_auto_converted',
    )

    list_filter = ('status', 'leave_type')
    search_fields = ('employee__emp_code',)
    readonly_fields = ('applied_date',)


@admin.register(LeaveApproval)
class LeaveApprovalAdmin(admin.ModelAdmin):
    list_display = (
        'leave',
        'approver',
        'approver_role',
        'status',
        'action_date',
    )

    list_filter = ('status', 'approver_role')
    readonly_fields = ('action_date',)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'year',
        'cl_balance',
        'ml_balance',
        'ol_balance',
        'lop_taken',
    )

    list_filter = ('year',)
