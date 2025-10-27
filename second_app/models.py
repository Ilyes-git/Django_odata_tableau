from django.db import models


class Author(models.Model):
    """Modèle Author pour tester OData avec une app différente"""
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Book(models.Model):
    """Modèle Book lié à Author"""
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    isbn = models.CharField(max_length=13, unique=True)
    pages = models.IntegerField()
    published_date = models.DateField()
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

