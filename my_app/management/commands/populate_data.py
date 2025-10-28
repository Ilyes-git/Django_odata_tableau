from __future__ import annotations

import random
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from faker import Faker

from my_app.models import Person, Car

BRANDS = [
    "Renault", "Peugeot", "Citroën", "Toyota", "Volkswagen",
    "Mercedes", "BMW", "Audi", "Dacia", "Ford",
]
MODELS_BY_BRAND = {
    "Renault": ["Clio", "Megane", "Talisman", "Captur"],
    "Peugeot": ["208", "308", "3008", "508"],
    "Citroën": ["C3", "C4", "C5 Aircross"],
    "Toyota": ["Yaris", "Corolla", "RAV4", "C-HR"],
    "Volkswagen": ["Golf", "Polo", "Tiguan", "Passat"],
    "Mercedes": ["A-Class", "C-Class", "E-Class"],
    "BMW": ["Serie 1", "Serie 3", "X1", "X3"],
    "Audi": ["A1", "A3", "A4", "Q3"],
    "Dacia": ["Sandero", "Duster", "Jogger"],
    "Ford": ["Fiesta", "Focus", "Kuga"],
}


class Command(BaseCommand):
    help = "Populate la base avec des persons et cars (seed de démo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--persons",
            type=int,
            default=20,
            help="Nombre de personnes à créer (default: 20).",
        )
        parser.add_argument(
            "--cars-per-person-min",
            type=int,
            default=0,
            help="Nombre min de voitures par personne (default: 0).",
        )
        parser.add_argument(
            "--cars-per-person-max",
            type=int,
            default=2,
            help="Nombre max de voitures par personne (default: 2).",
        )
        parser.add_argument(
            "--locale",
            type=str,
            default="fr_FR",
            help="Locale Faker (default: fr_FR).",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Supprime d'abord les données Person/Car existantes.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed RNG pour reproductibilité (default: 42).",
        )

    def handle(self, *args, **options):
        persons_count: int = options["persons"]
        cars_min: int = options["cars_per_person_min"]
        cars_max: int = options["cars_per_person_max"]
        locale: str = options["locale"]
        do_flush: bool = options["flush"]
        seed: int = options["seed"]

        if cars_min < 0 or cars_max < 0 or cars_max < cars_min:
            self.stderr.write(
                self.style.ERROR("Paramètres invalides: vérifier cars-per-person-min/max.")
            )
            return

        random.seed(seed)
        fake = Faker(locale)
        Faker.seed(seed)

        if do_flush:
            self.stdout.write("Suppression des données existantes…")
            # Ordre important (FK Car → Person)
            Car.objects.all().delete()
            Person.objects.all().delete()

        self.stdout.write(
            f"Génération de {persons_count} Person(s) avec {cars_min}–{cars_max} Car(s) chacun…"
        )

        created_persons = self._create_persons(fake, persons_count)
        self._create_cars_for_persons(fake, created_persons, cars_min, cars_max)

        self.stdout.write(self.style.SUCCESS("Seed terminé avec succès."))

    @transaction.atomic
    def _create_persons(self, fake: Faker, n: int) -> List[Person]:
        now = timezone.now()
        persons: List[Person] = []
        for _ in range(n):
            first_name = fake.first_name()
            last_name = fake.last_name()
            # birth_date facultative
            birth_date = (
                fake.date_between(start_date="-70y", end_date="-18y")
                if random.random() < 0.85
                else None
            )
            persons.append(
                Person(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                )
            )
        Person.objects.bulk_create(persons, batch_size=100)
        # Recharge avec IDs
        return list(Person.objects.order_by("-id")[:n][::-1])  # conserve l'ordre d'insertion

    @transaction.atomic
    def _create_cars_for_persons(
        self, fake: Faker, persons: List[Person], min_cars: int, max_cars: int
    ) -> None:
        cars: List[Car] = []
        for p in persons:
            count = random.randint(min_cars, max_cars)
            for _ in range(count):
                brand = random.choice(BRANDS)
                model = random.choice(MODELS_BY_BRAND.get(brand, ["Standard"]))
                year = random.randint(2005, timezone.now().year)
                cars.append(
                    Car(
                        brand=brand,
                        model=model,
                        year=year,
                        owner=p,
                    )
                )
        if cars:
            Car.objects.bulk_create(cars, batch_size=200)