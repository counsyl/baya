from django.db import models

# Create your models here.


class Blag(models.Model):
    name = models.CharField(max_length=128)


class BlagEntry(models.Model):
    blag = models.ForeignKey(Blag, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        verbose_name_plural = "Entries"


class PhotoBlagEntry(models.Model):
    blag = models.ForeignKey(Blag, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    # and a file field for a photo but whatever
