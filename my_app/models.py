from django.db import models

class Person(models.Model):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    birth_date = models.DateField(null=True, blank=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Car(models.Model):
    brand = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    year = models.IntegerField()
    owner = models.ForeignKey(Person, related_name="cars", on_delete=models.CASCADE)


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=0)
    category = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
