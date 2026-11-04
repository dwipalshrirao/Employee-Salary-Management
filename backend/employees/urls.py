"""Employee API routes."""

from django.urls import path

from employees.views import (
    EmployeeDeactivateView,
    EmployeeDetailView,
    EmployeeDirectReportsView,
    EmployeeHistoryView,
    EmployeeListView,
    EmployeeReactivateView,
)

urlpatterns = [
    path("employees", EmployeeListView.as_view(), name="employees-list"),
    path("employees/<int:pk>", EmployeeDetailView.as_view(), name="employees-detail"),
    path(
        "employees/<int:pk>/direct-reports",
        EmployeeDirectReportsView.as_view(),
        name="employees-direct-reports",
    ),
    path(
        "employees/<int:pk>/history",
        EmployeeHistoryView.as_view(),
        name="employees-history",
    ),
    path(
        "employees/<int:pk>/deactivate",
        EmployeeDeactivateView.as_view(),
        name="employees-deactivate",
    ),
    path(
        "employees/<int:pk>/reactivate",
        EmployeeReactivateView.as_view(),
        name="employees-reactivate",
    ),
]
