from django.urls import path
from .views import HealthCheckView, ProvidersView, SyncView, RawDataView

urlpatterns = [
    path('health/', HealthCheckView.as_view()),
    path('providers/', ProvidersView.as_view()),
    path('sync/', SyncView.as_view()),
    path('raw-data/', RawDataView.as_view()),
]
