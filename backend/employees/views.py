"""Employee API views."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED
from rest_framework.views import APIView

from common.serializers import PageQuerySerializer
from employees.selectors import (
    get_employee_detail,
    list_direct_reports,
    list_employee_history,
    list_employees,
)
from employees.serializers import (
    EmployeeCreateSerializer,
    EmployeeDetailSerializer,
    EmployeeListQuerySerializer,
    EmployeeListResponseSerializer,
    EmployeeUpdateSerializer,
    SalaryHistoryItemSerializer,
)
from employees.services.employees import (
    create_employee,
    deactivate_employee,
    reactivate_employee,
    update_employee,
)


class EmployeeListView(APIView):
    """List employees with filters, sorting and pagination."""

    @extend_schema(
        operation_id="employees-list",
        tags=["employees"],
        parameters=[EmployeeListQuerySerializer],
        responses={200: EmployeeListResponseSerializer},
    )
    def get(self, request, format=None):
        query = EmployeeListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = list_employees(**query.validated_data)
        return Response(EmployeeListResponseSerializer(result).data)

    @extend_schema(
        operation_id="employees-create",
        tags=["employees"],
        description="Create an employee and its initial hire history row.",
        request=EmployeeCreateSerializer,
        responses={201: EmployeeDetailSerializer},
    )
    def post(self, request, format=None):
        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = create_employee(serializer.validated_data)
        return Response(
            EmployeeDetailSerializer(employee).data,
            status=HTTP_201_CREATED,
        )


class EmployeeDetailView(APIView):
    """Return one employee with local-currency amounts."""

    @extend_schema(
        operation_id="employees-detail",
        tags=["employees"],
        responses={200: EmployeeDetailSerializer},
    )
    def get(self, request, pk, format=None):
        employee = get_employee_detail(pk)
        return Response(EmployeeDetailSerializer(employee).data)

    @extend_schema(
        operation_id="employees-update",
        tags=["employees"],
        description="Partially update an employee and record pay changes.",
        request=EmployeeUpdateSerializer,
        responses={200: EmployeeDetailSerializer},
    )
    def patch(self, request, pk, format=None):
        serializer = EmployeeUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = update_employee(pk, serializer.validated_data)
        return Response(EmployeeDetailSerializer(get_employee_detail(employee.id)).data)


class EmployeeDirectReportsView(APIView):
    """Return an employee's direct reports with pagination."""

    @extend_schema(
        operation_id="employees-direct-reports",
        tags=["employees"],
        parameters=[PageQuerySerializer],
        responses={200: EmployeeListResponseSerializer},
    )
    def get(self, request, pk, format=None):
        query = PageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = list_direct_reports(pk, **query.validated_data)
        return Response(EmployeeListResponseSerializer(result).data)


class EmployeeHistoryView(APIView):
    """Return one employee's salary history, newest first."""

    @extend_schema(
        operation_id="employees-history",
        tags=["employees"],
        responses={200: SalaryHistoryItemSerializer(many=True)},
    )
    def get(self, request, pk, format=None):
        rows = list_employee_history(pk)
        return Response(SalaryHistoryItemSerializer(rows, many=True).data)


class EmployeeDeactivateView(APIView):
    """Soft-delete an employee."""

    @extend_schema(
        operation_id="employees-deactivate",
        tags=["employees"],
        request=None,
        responses={200: EmployeeDetailSerializer},
    )
    def post(self, request, pk, format=None):
        employee = deactivate_employee(pk)
        return Response(EmployeeDetailSerializer(get_employee_detail(employee.id)).data)


class EmployeeReactivateView(APIView):
    """Restore a soft-deleted employee."""

    @extend_schema(
        operation_id="employees-reactivate",
        tags=["employees"],
        request=None,
        responses={200: EmployeeDetailSerializer},
    )
    def post(self, request, pk, format=None):
        employee = reactivate_employee(pk)
        return Response(EmployeeDetailSerializer(get_employee_detail(employee.id)).data)
