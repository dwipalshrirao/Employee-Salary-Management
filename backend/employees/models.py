from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from catalog.models import Country, Department, JobTitle


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    full_name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    job_title = models.ForeignKey(
        JobTitle,
        on_delete=models.PROTECT,
        related_name="employees",
    )
    country = models.ForeignKey(
        Country,
        to_field="code",
        db_column="country_code",
        on_delete=models.PROTECT,
        related_name="employees",
    )
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="direct_reports",
    )
    hire_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    base_salary_cents = models.BigIntegerField()
    bonus_cents = models.BigIntegerField(default=0)
    allowances_cents = models.BigIntegerField(default=0)
    total_comp_cents = models.GeneratedField(
        expression=F("base_salary_cents") + F("bonus_cents") + F("allowances_cents"),
        output_field=models.BigIntegerField(),
        db_persist=True,
    )
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "employees"
        constraints = [
            models.CheckConstraint(
                condition=Q(base_salary_cents__gt=0),
                name="ck_emp_base_positive",
            ),
            models.CheckConstraint(
                condition=Q(bonus_cents__gte=0),
                name="ck_emp_bonus_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(allowances_cents__gte=0),
                name="ck_emp_allowances_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("active", "inactive")),
                name="ck_emp_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(manager_id__isnull=True) | ~Q(manager_id=F("id")),
                name="ck_emp_manager_not_self",
            ),
            models.UniqueConstraint(Lower("email"), name="uniq_employee_email_lower"),
        ]
        indexes = [
            models.Index(
                fields=["status", "country"],
                name="idx_emp_status_country",
            ),
            models.Index(
                fields=["status", "department"],
                name="idx_emp_status_dept",
            ),
            models.Index(fields=["job_title"], name="idx_emp_title"),
            models.Index(fields=["manager"], name="idx_emp_manager"),
            models.Index(Lower("full_name"), name="idx_emp_name"),
        ]

    def __str__(self):
        return self.full_name


class SalaryHistory(models.Model):
    class ChangeType(models.TextChoices):
        HIRE = "hire", "Hire"
        MANUAL_EDIT = "manual_edit", "Manual edit"
        BULK_UPDATE = "bulk_update", "Bulk update"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="salary_history",
    )
    effective_date = models.DateField()
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    reason = models.TextField(null=True, blank=True)
    batch_id = models.UUIDField(null=True, blank=True)
    base_salary_cents = models.BigIntegerField()
    bonus_cents = models.BigIntegerField()
    allowances_cents = models.BigIntegerField()
    prev_base_salary_cents = models.BigIntegerField(null=True, blank=True)
    prev_bonus_cents = models.BigIntegerField(null=True, blank=True)
    prev_allowances_cents = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "salary_history"
        constraints = [
            models.CheckConstraint(
                condition=Q(change_type__in=("hire", "manual_edit", "bulk_update")),
                name="ck_history_change_type_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["employee", "-effective_date", "-id"],
                name="idx_history_employee_effective",
            ),
            models.Index(
                fields=["batch_id"],
                name="idx_history_batch",
                condition=Q(batch_id__isnull=False),
            ),
            models.Index(
                fields=["-effective_date", "-id"],
                name="idx_history_effective",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None and SalaryHistory.objects.filter(pk=self.pk).exists():
            raise ValueError("SalaryHistory is append-only")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee_id} {self.effective_date} {self.change_type}"
