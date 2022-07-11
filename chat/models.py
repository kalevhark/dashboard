from django.db import models

# katsetamiseks kroonika jaoks 16.06.2022
class Objekt(models.Model):
    nimi = models.CharField(
        'Kohanimi',
        max_length=200,
        help_text='Kohanimi/nimed'
    )
    # Seotud:
    objektid = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Kohad'
    )
    eellased = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name='Eellased',
        related_name='j2rglane',
        symmetrical=False
    )

    def __repr__(self):
        return self.nimi

    def __str__(self):
        return self.nimi
