from django.db import models


class CloudExpense(models.Model):
    """
    Represents a cloud expense record stored in PostgreSQL.
    Indexed for fast aggregation queries by area and date (ASR 1 - Performance).
    """
    area = models.CharField(max_length=100, db_index=True)
    department = models.CharField(max_length=100, db_index=True)
    provider = models.CharField(max_length=50, default='aws')
    service_name = models.CharField(max_length=200)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=4)
    currency = models.CharField(max_length=10, default='USD')
    expense_date = models.DateField(db_index=True)
    company_id = models.IntegerField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cloud_expenses'
        indexes = [
            # Composite index for the ASR 1 query pattern:
            # Filter by company_id + date range, GROUP BY area
            models.Index(
                fields=['company_id', 'expense_date', 'area'],
                name='idx_expense_company_date_area'
            ),
            models.Index(
                fields=['area', 'expense_date'],
                name='idx_expense_area_date'
            ),
        ]
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.area} | {self.expense_date} | ${self.amount_usd}"


class AuditLog(models.Model):
    """
    Stores audit records for unauthorized access attempts (ASR 2 - Security).
    """
    ACTION_CHOICES = [
        ('ACCESS_DENIED', 'Access Denied'),
        ('ACCESS_GRANTED', 'Access Granted'),
        ('INVALID_TOKEN', 'Invalid Token'),
        ('MISSING_TOKEN', 'Missing Token'),
        ('INSUFFICIENT_ROLE', 'Insufficient Role'),
    ]

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    endpoint = models.CharField(max_length=500)
    user_sub = models.CharField(max_length=255, null=True, blank=True)
    user_roles = models.JSONField(default=list)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['timestamp'], name='idx_audit_timestamp'),
            models.Index(fields=['action'], name='idx_audit_action'),
        ]

    def __str__(self):
        return f"{self.action} | {self.user_sub} | {self.timestamp}"
