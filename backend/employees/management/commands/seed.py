"""Management command that creates reference data and a deterministic seed."""

import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.crypto import get_random_string

from accounts.models import HrUser
from employees.models import Employee, SalaryHistory
from employees.seeding.generator import SeedGenerator
from employees.seeding.reference import create_reference_data
from employees.seeding.verify import verify_seed


class Command(BaseCommand):
    """Seed reference data, employees and salary history in one command."""

    help = "Seed reference data, employees and salary history."

    def add_arguments(self, parser):
        parser.add_argument("--employees", type=int, default=10_000)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--verify", action="store_true")

    def handle(self, *args, **options):
        """Validate options, replace data when requested, then optionally verify."""
        employee_count = options["employees"]
        seed = options["seed"]
        reset = options["reset"]
        verify = options["verify"]

        if employee_count < 25:
            raise CommandError("--employees must be at least 25.")

        if Employee.objects.exists():
            # A verify-only run must never delete existing data.
            if verify and not reset:
                verify_seed(self.stdout)
                return
            if not reset:
                raise CommandError(
                    "Employees already exist. Run with --reset to replace the seed."
                )

        if reset:
            call_command("flush", interactive=False, verbosity=0)

        started_at = time.perf_counter()
        self._create_hr_user()

        # Seeding is a bulk import, so relax SQLite durability for this run and
        # restore the configured synchronous mode in the finally block.
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA synchronous = OFF")
        try:
            with transaction.atomic():
                create_reference_data()

            generator = SeedGenerator(employee_count, seed)
            employees, history_rows = generator.build()

            with transaction.atomic():
                Employee.objects.bulk_create(employees, batch_size=1_000)

            with transaction.atomic():
                SalaryHistory.objects.bulk_create(history_rows, batch_size=1_000)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA synchronous = NORMAL")

        elapsed = time.perf_counter() - started_at
        self.stdout.write(
            f"seed: {Employee.objects.count()} employees, "
            f"{SalaryHistory.objects.count()} history rows in {elapsed:.2f}s."
        )

        if verify:
            verify_seed(self.stdout)

    def _create_hr_user(self):
        """Create the HR account once, or reuse the existing account by email."""
        email = os.getenv("SEED_HR_EMAIL", "hr@acme.example")
        password = os.getenv("SEED_HR_PASSWORD", "")

        if HrUser.objects.filter(email__iexact=email).exists():
            return

        generated_password = not password
        if generated_password:
            password = get_random_string(16)

        user = HrUser(email=email, full_name="HR Manager")
        user.set_password(password)
        user.save()

        if generated_password:
            self.stdout.write(
                f"Generated HR password for {email}: {password} (shown once)"
            )
