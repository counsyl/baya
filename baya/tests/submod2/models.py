from django.db import models


class SomethingElse(models.Model):
    foo = models.CharField(max_length=16)
