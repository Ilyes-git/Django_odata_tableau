from django.db import models
from django.contrib.auth.models import User
import re

incremented_name = re.compile(r"(?P<rootname>.+)_(?P<indice>[9-9]+')")


class Folder(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    username = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.id is None:
            #in case we try to create a new folder 
            try:
                alreadyUsedName = Folder.objects.get(name=self.name, parent=self.parent, username=self.username)
                if alreadyUsedName is not None:
                    found = False
                    indice = 0

                    while not found:
                        essai = f"{self.name}_{indice}"
                        try:
                            Folder.objects.get(name=essai, parent=self.parent, username=self.username)
                            indice = indice + 1
                        except:
                            found = True
                            self.name = essai
            except:
                pass
        super(Folder, self).save(*args, **kwargs)


class Map(models.Model):
    name = models.CharField(max_length=255)
    data = models.JSONField()
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='maps')
    username = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.id is None:
            #in case we try to create a new map file
            try:
                alreadyUsedName = Map.objects.get(name=self.name, folder=self.folder, username=self.username)
                if alreadyUsedName is not None:
                    found = False
                    indice = 0

                    while not found:
                        essai = f"{self.name}_{indice}"
                        try:
                            Map.objects.get(name=essai, folder=self.folder, username=self.username)
                            indice = indice + 1
                        except:
                            found = True
                            self.name = essai
            except:
                pass
        super(Map, self).save(*args, **kwargs)
