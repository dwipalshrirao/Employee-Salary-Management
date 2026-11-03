"""Employee API views."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from employees.selectors import list_employees
from employees.serializers import (
    EmployeeListQuerySerializer,
    EmployeeListResponseSerializer,
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
