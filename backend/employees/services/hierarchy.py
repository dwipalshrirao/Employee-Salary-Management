"""Hierarchy validation shared by employee writes."""

from rest_framework.exceptions import ValidationError

from employees.models import Employee


def validate_manager(employee_id, manager_id):
    """Return an active manager, or raise a validation error."""
    if manager_id is None:
        return None

    manager = Employee.objects.filter(pk=manager_id).first()
    if manager is None:
        raise ValidationError({"manager_id": ["Manager does not exist."]})
    if manager.status != Employee.Status.ACTIVE:
        raise ValidationError({"manager_id": ["Manager must be active."]})

    if employee_id is not None:
        visited = set()
        current = manager
        while current.manager_id is not None:
            if current.id in visited or len(visited) > Employee.objects.count():
                raise ValidationError({"manager_id": ["Manager cycle detected."]})
            if current.id == employee_id:
                raise ValidationError({"manager_id": ["Manager cannot be self or a report."]})
            visited.add(current.id)
            current = Employee.objects.get(pk=current.manager_id)
        if current.id == employee_id:
            raise ValidationError({"manager_id": ["Manager cannot be self or a report."]})

    return manager
