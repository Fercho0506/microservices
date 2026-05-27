from django.urls import path, include

urlpatterns = [
    path('finops/', include('expenses.urls')),
]
