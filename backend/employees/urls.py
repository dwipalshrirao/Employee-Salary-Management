"""Employee API routes."""

from django.urls import path

from employees.views import EmployeeListView

urlpatterns = [
    path("employees", EmployeeListView.as_view(), name="employees-list"),
]
