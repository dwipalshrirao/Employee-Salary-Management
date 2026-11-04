"""Serializers for employee list queries and responses."""

from decimal import Decimal

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.models import Country, Department, JobTitle
from common.clock import get_clock
from common.serializers import PageQuerySerializer, StrictSerializer
from employees.local_currency import local_amounts
from employees.models import Employee

MAX_AMOUNT_CENTS = 1_000_000_000

SORT_BY_CHOICES = (
    "full_name",
    "email",
    "hire_date",
    "base_salary",
    "total_comp",
    "department",
    "job_title",
    "country",
)


class EmployeeListQuerySerializer(PageQuerySerializer):
    q = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country_code = serializers.CharField(
        max_length=2,
        required=False,
        allow_blank=True,
    )
    department_id = serializers.IntegerField(required=False)
    job_title_id = serializers.IntegerField(required=False)
    manager_id = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(
        choices=("active", "inactive", "all"),
        default="active",
    )
    sort_by = serializers.ChoiceField(choices=SORT_BY_CHOICES, default="full_name")
    sort_dir = serializers.ChoiceField(choices=("asc", "desc"), default="asc")


class EmployeeManagerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class EmployeeDepartmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class EmployeeJobTitleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class EmployeeCountrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class EmployeeListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    department = EmployeeDepartmentSerializer()
    job_title = EmployeeJobTitleSerializer()
    country = EmployeeCountrySerializer()
    manager = EmployeeManagerSerializer(allow_null=True)
    hire_date = serializers.DateField()
    status = serializers.CharField()
    base_salary_cents = serializers.IntegerField()
    bonus_cents = serializers.IntegerField()
    allowances_cents = serializers.IntegerField()
    total_comp_cents = serializers.IntegerField()


class EmployeeListResponseSerializer(serializers.Serializer):
    items = EmployeeListItemSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()


class LocalAmountsSerializer(serializers.Serializer):
    currency_code = serializers.CharField()
    rate_per_usd = serializers.FloatField()
    base_salary_cents = serializers.IntegerField()
    bonus_cents = serializers.IntegerField()
    allowances_cents = serializers.IntegerField()
    total_comp_cents = serializers.IntegerField()


class EmployeeDetailSerializer(EmployeeListItemSerializer):
    direct_reports_count = serializers.IntegerField()
    local = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    @extend_schema_field(LocalAmountsSerializer)
    def get_local(self, employee):
        return local_amounts(employee)


class SalaryAmountsSerializer(serializers.Serializer):
    base_salary_cents = serializers.IntegerField()
    bonus_cents = serializers.IntegerField()
    allowances_cents = serializers.IntegerField()
    total_comp_cents = serializers.IntegerField()


class SalaryHistoryItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    effective_date = serializers.DateField()
    change_type = serializers.CharField()
    reason = serializers.CharField(allow_null=True)
    batch_id = serializers.UUIDField(allow_null=True)
    created_at = serializers.DateTimeField()
    new = serializers.SerializerMethodField()
    previous = serializers.SerializerMethodField()

    @extend_schema_field(SalaryAmountsSerializer)
    def get_new(self, row):
        return {
            "base_salary_cents": row.base_salary_cents,
            "bonus_cents": row.bonus_cents,
            "allowances_cents": row.allowances_cents,
            "total_comp_cents": (
                row.base_salary_cents + row.bonus_cents + row.allowances_cents
            ),
        }

    @extend_schema_field(SalaryAmountsSerializer)
    def get_previous(self, row):
        if row.change_type == "hire" or (
            row.prev_base_salary_cents is None
            and row.prev_bonus_cents is None
            and row.prev_allowances_cents is None
        ):
            return None
        return {
            "base_salary_cents": row.prev_base_salary_cents,
            "bonus_cents": row.prev_bonus_cents,
            "allowances_cents": row.prev_allowances_cents,
            "total_comp_cents": (
                row.prev_base_salary_cents
                + row.prev_bonus_cents
                + row.prev_allowances_cents
            ),
        }


class EmployeeCreateSerializer(StrictSerializer):
    full_name = serializers.CharField(max_length=120)
    email = serializers.EmailField(max_length=254)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="department",
    )
    job_title_id = serializers.PrimaryKeyRelatedField(
        queryset=JobTitle.objects.all(),
        source="job_title",
    )
    country_code = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        source="country",
    )
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="manager",
        allow_null=True,
        required=False,
    )
    hire_date = serializers.DateField()
    base_salary_cents = serializers.IntegerField(
        min_value=1,
        max_value=MAX_AMOUNT_CENTS,
    )
    bonus_cents = serializers.IntegerField(
        min_value=0,
        max_value=MAX_AMOUNT_CENTS,
        default=0,
    )
    allowances_cents = serializers.IntegerField(
        min_value=0,
        max_value=MAX_AMOUNT_CENTS,
        default=0,
    )

    def validate_hire_date(self, value):
        if value > get_clock().today():
            raise serializers.ValidationError("Hire date cannot be in the future.")
        return value


class EmployeeUpdateSerializer(StrictSerializer):
    full_name = serializers.CharField(max_length=120, required=False)
    email = serializers.EmailField(max_length=254, required=False)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source="department",
        required=False,
    )
    job_title_id = serializers.PrimaryKeyRelatedField(
        queryset=JobTitle.objects.all(),
        source="job_title",
        required=False,
    )
    country_code = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        source="country",
        required=False,
    )
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source="manager",
        allow_null=True,
        required=False,
    )
    hire_date = serializers.DateField(required=False)
    base_salary_cents = serializers.IntegerField(
        min_value=1,
        max_value=MAX_AMOUNT_CENTS,
        required=False,
    )
    bonus_cents = serializers.IntegerField(
        min_value=0,
        max_value=MAX_AMOUNT_CENTS,
        required=False,
    )
    allowances_cents = serializers.IntegerField(
        min_value=0,
        max_value=MAX_AMOUNT_CENTS,
        required=False,
    )
    change_reason = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
    )

    def validate_hire_date(self, value):
        if value > get_clock().today():
            raise serializers.ValidationError("Hire date cannot be in the future.")
        return value


class BulkUpdateFilterSerializer(StrictSerializer):
    country_code = serializers.CharField(
        max_length=2,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    department_id = serializers.IntegerField(required=False, allow_null=True)
    job_title_id = serializers.IntegerField(required=False, allow_null=True)
    manager_id = serializers.IntegerField(required=False, allow_null=True)


class BulkUpdatePreviewSerializer(StrictSerializer):
    filter = BulkUpdateFilterSerializer(required=False)
    apply_to_all = serializers.BooleanField(default=False)
    component = serializers.ChoiceField(choices=("base", "bonus", "allowances"))
    mode = serializers.ChoiceField(choices=("percent", "fixed_amount"))
    percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal(str(settings.BULK_MIN_PERCENT)),
        max_value=Decimal(str(settings.BULK_MAX_PERCENT)),
    )
    amount_cents = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=MAX_AMOUNT_CENTS,
    )

    def validate(self, attrs):
        filters = attrs.get("filter") or {}
        has_filter = any(
            filters.get(field) not in (None, "")
            for field in ("country_code", "department_id", "job_title_id", "manager_id")
        )
        if not has_filter and not attrs.get("apply_to_all"):
            raise serializers.ValidationError(
                {
                    "filter": [
                        "Choose a filter or set apply_to_all to true."
                    ]
                }
            )

        mode = attrs["mode"]
        percentage = attrs.get("percentage")
        amount_cents = attrs.get("amount_cents")
        if mode == "percent":
            if percentage is None or amount_cents is not None:
                raise serializers.ValidationError(
                    {"percentage": ["Provide only percentage for percent mode."]}
                )
            if percentage == 0:
                raise serializers.ValidationError(
                    {"percentage": ["Percentage cannot be zero."]}
                )
        else:
            if amount_cents is None or percentage is not None:
                raise serializers.ValidationError(
                    {"amount_cents": ["Provide only amount_cents for fixed_amount mode."]}
                )
        return attrs


class BulkUpdateApplySerializer(BulkUpdatePreviewSerializer):
    expected_count = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=200)


class BulkUpdateSampleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    before_cents = serializers.IntegerField()
    after_cents = serializers.IntegerField()


class BulkUpdatePreviewResponseSerializer(serializers.Serializer):
    component = serializers.CharField()
    mode = serializers.CharField()
    affected_count = serializers.IntegerField()
    sum_before_cents = serializers.IntegerField()
    sum_after_cents = serializers.IntegerField()
    sum_delta_cents = serializers.IntegerField()
    sample = BulkUpdateSampleSerializer(many=True)


class BulkUpdateApplyResponseSerializer(serializers.Serializer):
    batch_id = serializers.UUIDField()
    component = serializers.CharField()
    affected_count = serializers.IntegerField()
    sum_delta_cents = serializers.IntegerField()
