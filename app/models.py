from django.db import models

class Log(models.Model):
    data = models.JSONField(null=True)

    def __str__(self):
        return self.data.get('dateString', self.id)