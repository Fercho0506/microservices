from django.urls import path
from .views import ExpensesByAreaView, HealthCheckView, SeedDataView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health'),
    path('expenses/by-area/', ExpensesByAreaView.as_view(), name='expenses-by-area'),
    path('expenses/seed/', SeedDataView.as_view(), name='expenses-seed'),
]
