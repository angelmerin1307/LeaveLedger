from .models import AuditLog

def log_action(*, actor, module, action):
    """
    Centralized audit logger.
    Always use keyword arguments.
    """
    AuditLog.objects.create(
        user=actor,
        module=module,
        action=action
    )
