from django.http import HttpResponse
from .network_utils import ping_device


def test_ping(request):
    ip = "127.0.0.1"

    if ping_device(ip):
        return HttpResponse("Device is ONLINE")
    else:
        return HttpResponse("Device is OFFLINE")