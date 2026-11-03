"""Serializers for employee list queries and responses."""

from rest_framework import serializers

from common.serializers import PageQuerySerializer

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
