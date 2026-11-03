from django.db import models
from django.db.models import Q


class CurrencyRate(models.Model):
    """USD conversion rate for one ISO currency code."""

    currency_code = models.CharField(max_length=3, primary_key=True)
    rate_per_usd = models.FloatField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "currency_rates"
        constraints = [
            models.CheckConstraint(
                condition=Q(currency_code__regex=r"^[A-Z]{3}$"),
                name="ck_currency_code_format",
            ),
            models.CheckConstraint(
                condition=Q(rate_per_usd__gt=0),
                name="ck_currency_rate_positive",
            ),
        ]

    def __str__(self):
        return self.currency_code


class Country(models.Model):
    """Country lookup with its primary currency."""

    code = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    currency_code = models.ForeignKey(
        CurrencyRate,
        db_column="currency_code",
        on_delete=models.PROTECT,
        related_name="countries",
    )

    class Meta:
        db_table = "countries"
        constraints = [
            models.CheckConstraint(
                condition=Q(code__regex=r"^[A-Z]{2}$"),
                name="ck_country_code_format",
            ),
        ]

    def __str__(self):
        return self.name


class Department(models.Model):
    """Organizational department used by employees and analytics."""

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "departments"

    def __str__(self):
        return self.name


class JobTitle(models.Model):
    """Job title and its compensation level from 1 to 7."""

    name = models.CharField(max_length=100, unique=True)
    level = models.IntegerField()

    class Meta:
        db_table = "job_titles"
        constraints = [
            models.CheckConstraint(
                condition=Q(level__gte=1) & Q(level__lte=7),
                name="ck_job_title_level_range",
            ),
        ]

    def __str__(self):
        return self.name
