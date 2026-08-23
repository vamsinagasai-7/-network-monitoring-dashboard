from django.db import models


class Device(models.Model):
    name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField()
    device_type = models.CharField(max_length=50)
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return self.name