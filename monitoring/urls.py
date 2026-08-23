from django.urls import path
from . import views

urlpatterns = [
    path("test-ping/", views.test_ping, name="test_ping"),
]