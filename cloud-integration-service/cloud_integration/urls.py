from django.urls import path, include

urlpatterns = [
    path('integration/', include('integration.urls')),
]
