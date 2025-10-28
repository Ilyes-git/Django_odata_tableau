from django.core.management.base import BaseCommand
from faker import Faker
from vessel.models import (
    ShipClass,
    Port,
    Organisation,
    Role,
    Purpose,
    Task,
    Vessel,
    VesselQualification,
    VesselPurpose,
    OperationalParameter,
    VesselStakeholder,
    VesselFlagMmsiHistory,
    Project,
    VesselProjectHistory,
)
from datetime import date, timedelta
import random

fake = Faker()


class Command(BaseCommand):
    help = "Populate vessel database with 100 records for each model using Faker"

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100,
            help='Number of records to generate for each model (default: 100)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear = options['clear']

        if clear:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            VesselProjectHistory.objects.all().delete()
            VesselFlagMmsiHistory.objects.all().delete()
            VesselStakeholder.objects.all().delete()
            OperationalParameter.objects.all().delete()
            VesselPurpose.objects.all().delete()
            VesselQualification.objects.all().delete()
            Vessel.objects.all().delete()
            Task.objects.all().delete()
            Purpose.objects.all().delete()
            Role.objects.all().delete()
            Organisation.objects.all().delete()
            Port.objects.all().delete()
            ShipClass.objects.all().delete()
            Project.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Data cleared'))

        try:
            # 1. ShipClass
            self.stdout.write('📦 Generating ShipClass...')
            self._generate_ship_classes(count)
            ship_classes = list(ShipClass.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(ship_classes)} ShipClass'))

            # 2. Port
            self.stdout.write('📦 Generating Port...')
            self._generate_ports(count)
            ports = list(Port.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(ports)} Port'))

            # 3. Organisation
            self.stdout.write('📦 Generating Organisation...')
            self._generate_organisations(count)
            organisations = list(Organisation.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(organisations)} Organisation'))

            # 4. Role
            self.stdout.write('📦 Generating Role...')
            self._generate_roles(count)
            roles = list(Role.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(roles)} Role'))

            # 5. Purpose
            self.stdout.write('📦 Generating Purpose...')
            self._generate_purposes(count)
            purposes = list(Purpose.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(purposes)} Purpose'))

            # 6. Task
            self.stdout.write('📦 Generating Task...')
            self._generate_tasks(count)
            tasks = list(Task.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(tasks)} Task'))

            # 7. Vessel
            self.stdout.write('📦 Generating Vessel...')
            self._generate_vessels(count, ship_classes, ports)
            vessels = list(Vessel.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(vessels)} Vessel'))

            # 8. VesselQualification
            self.stdout.write('📦 Generating VesselQualification...')
            self._generate_vessel_qualifications(count, vessels, tasks)
            vq_count = VesselQualification.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Created {vq_count} VesselQualification'))

            # 9. VesselPurpose
            self.stdout.write('📦 Generating VesselPurpose...')
            self._generate_vessel_purposes(count, vessels, purposes)
            vp_count = VesselPurpose.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Created {vp_count} VesselPurpose'))

            # 10. OperationalParameter
            self.stdout.write('📦 Generating OperationalParameter...')
            self._generate_operational_parameters(count, ship_classes, purposes, tasks)
            op_count = OperationalParameter.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Created {op_count} OperationalParameter'))

            # 11. VesselStakeholder
            self.stdout.write('📦 Generating VesselStakeholder...')
            self._generate_vessel_stakeholders(count, vessels, organisations, roles)
            vs_count = VesselStakeholder.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Created {vs_count} VesselStakeholder'))

            # 12. VesselFlagMmsiHistory
            self.stdout.write('📦 Generating VesselFlagMmsiHistory...')
            self._generate_vessel_flag_mmsi_histories(count, vessels)
            vfmh_count = VesselFlagMmsiHistory.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Created {vfmh_count} VesselFlagMmsiHistory'))

            # 13. Project
            self.stdout.write('📦 Generating Project...')
            self._generate_projects(count)
            projects = list(Project.objects.all())
            self.stdout.write(self.style.SUCCESS(f'✅ Created {len(projects)} Project'))

            # 14. VesselProjectHistory
            self.stdout.write('📦 Generating VesselProjectHistory...')
            self._generate_vessel_project_histories(count, projects, vessels, tasks)
            vph_count = VesselProjectHistory.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✅ Created {vph_count} VesselProjectHistory'))

            self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully populated {count} records for each model!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise

    def _generate_ship_classes(self, count):
        """Generate ShipClass records"""
        records = []
        for i in range(count):
            name = f"{fake.word().capitalize()}-ShipClass-{i}"
            records.append(ShipClass(
                name=name,
                transit_speed_kn=round(fake.random.uniform(8, 20), 2),
                draught_m=round(fake.random.uniform(5, 15), 2)
            ))
        ShipClass.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_ports(self, count):
        """Generate Port records"""
        ports = []
        for i in range(count):
            ports.append(Port(
                wpi_number=fake.bothify('???-####'),
                name=f"Port-{i}",
                un_locode=fake.bothify('??-???'),
                world_water_body=fake.random.choice(['Atlantic Ocean', 'Pacific Ocean', 'Indian Ocean', 'Mediterranean Sea', 'North Sea']),
                tidal_range_m=round(fake.random.uniform(0, 12), 2),
                entrance_width_m=round(fake.random.uniform(50, 500), 2),
                anchorage_depth_m=round(fake.random.uniform(10, 50), 2),
                oil_terminal_depth_m=round(fake.random.uniform(8, 40), 2),
                maximum_vessel_length_m=round(fake.random.uniform(200, 400), 2),
                maximum_vessel_draft_m=round(fake.random.uniform(10, 15), 2),
                supplies_potable_water=fake.boolean(),
                supplies_fuel_oil=fake.boolean(),
                dry_dock=fake.random.choice(['SMALL', 'MEDIUM', 'LARGE']),
                latitude=round(fake.latitude(), 4),
                longitude=round(fake.longitude(), 4)
            ))
        Port.objects.bulk_create(ports, ignore_conflicts=True)

    def _generate_organisations(self, count):
        """Generate Organisation records"""
        organisations = []
        for i in range(count):
            organisations.append(Organisation(
                name=f"{fake.company()}-{i}",
                acronym=fake.bothify('???').upper(),
                address=fake.address()
            ))
        Organisation.objects.bulk_create(organisations, ignore_conflicts=True)

    def _generate_roles(self, count):
        """Generate Role records"""
        records = []
        for i in range(count):
            records.append(Role(
                name=f"Role-{i}"
            ))
        Role.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_purposes(self, count):
        """Generate Purpose records"""
        purposes = []
        for i in range(count):
            purposes.append(Purpose(
                name=f"Purpose-{i}",
                description=fake.sentence()
            ))
        Purpose.objects.bulk_create(purposes, ignore_conflicts=True)

    def _generate_tasks(self, count):
        """Generate Task records"""
        tasks = []
        seen_acronyms = set()
        for i in range(count):
            while True:
                acronym = f"{fake.bothify('???').upper()}-{i}"
                if acronym not in seen_acronyms:
                    seen_acronyms.add(acronym)
                    break
            tasks.append(Task(
                acronym=acronym,
                full_name=fake.sentence(nb_words=4),
                description=fake.paragraph()
            ))
        Task.objects.bulk_create(tasks, ignore_conflicts=True)

    def _generate_vessels(self, count, ship_classes, ports):
        """Generate Vessel records"""
        vessels = []
        for i in range(count):
            vessels.append(Vessel(
                imo=9000000 + i,
                name=f"Vessel-{fake.word().capitalize()}-{i}",
                acronym=fake.bothify('???').upper(),
                main_lay=fake.boolean(),
                dynamic_positioning=fake.word(),
                year_built=fake.random.randint(2000, 2024),
                length_overall_m=round(fake.random.uniform(50, 400), 2),
                width_m=round(fake.random.uniform(10, 60), 2),
                draught_m=round(fake.random.uniform(3, 15), 2),
                gross_tonnage_t=round(fake.random.uniform(1000, 200000), 2),
                deadweight_t=round(fake.random.uniform(2000, 300000), 2),
                max_speed_kn=round(fake.random.uniform(10, 25), 2),
                transit_speed_kn=round(fake.random.uniform(12, 22), 2),
                fuel_capacity_t=round(fake.random.uniform(100, 5000), 2),
                fuel_safety_level_t=round(fake.random.uniform(50, 2500), 2),
                ship_class_id=fake.random.choice(ship_classes).id,
                port_id=fake.random.choice(ports).id
            ))
        Vessel.objects.bulk_create(vessels, ignore_conflicts=True)

    def _generate_vessel_qualifications(self, count, vessels, tasks):
        """Generate VesselQualification records"""
        records = []
        created_pairs = set()
        for i in range(count):
            try:
                vessel = fake.random.choice(vessels)
                task = fake.random.choice(tasks)
                pair = (vessel.id, task.id)
                if pair not in created_pairs:
                    records.append(VesselQualification(
                        vessel_id=vessel.id,
                        task_id=task.id
                    ))
                    created_pairs.add(pair)
            except:
                continue
        VesselQualification.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_vessel_purposes(self, count, vessels, purposes):
        """Generate VesselPurpose records"""
        records = []
        created_pairs = set()
        for i in range(count):
            try:
                vessel = fake.random.choice(vessels)
                purpose = fake.random.choice(purposes)
                pair = (vessel.id, purpose.id)
                if pair not in created_pairs:
                    records.append(VesselPurpose(
                        vessel_id=vessel.id,
                        purpose_id=purpose.id,
                        primary_purpose=fake.boolean()
                    ))
                    created_pairs.add(pair)
            except:
                continue
        VesselPurpose.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_operational_parameters(self, count, ship_classes, purposes, tasks):
        """Generate OperationalParameter records"""
        records = []
        created_triples = set()
        for i in range(count):
            try:
                ship_class = fake.random.choice(ship_classes)
                purpose = fake.random.choice(purposes)
                task = fake.random.choice(tasks)
                triple = (ship_class.id, purpose.id, task.id)
                if triple not in created_triples:
                    records.append(OperationalParameter(
                        timewindow_h=fake.random.randint(1, 72),
                        max_wind_speed_kn=round(fake.random.uniform(10, 50), 2),
                        max_wave_m=round(fake.random.uniform(1, 10), 2),
                        max_current_kn=round(fake.random.uniform(0.5, 5), 2),
                        standard_consumption=fake.random.randint(100, 5000),
                        theoretical_speed_kn=fake.random.randint(10, 25),
                        applicable_speed_kn=fake.random.randint(8, 23),
                        ship_class_id=ship_class.id,
                        purpose_id=purpose.id,
                        task_id=task.id
                    ))
                    created_triples.add(triple)
            except:
                continue
        OperationalParameter.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_vessel_stakeholders(self, count, vessels, organisations, roles):
        """Generate VesselStakeholder records"""
        records = []
        created_triples = set()
        for i in range(count):
            try:
                vessel = fake.random.choice(vessels)
                organisation = fake.random.choice(organisations)
                role = fake.random.choice(roles)
                triple = (organisation.id, role.id, vessel.id)
                if triple not in created_triples:
                    records.append(VesselStakeholder(
                        vessel_id=vessel.id,
                        organisation_id=organisation.id,
                        role_id=role.id
                    ))
                    created_triples.add(triple)
            except:
                continue
        VesselStakeholder.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_vessel_flag_mmsi_histories(self, count, vessels):
        """Generate VesselFlagMmsiHistory records"""
        records = []
        for i in range(count):
            start_date = fake.date_object()
            end_date = start_date + timedelta(days=fake.random.randint(1, 365))
            records.append(VesselFlagMmsiHistory(
                flag_start_date=start_date,
                flag_end_date=end_date,
                mmsi=219000000 + fake.random.randint(0, 999999),
                vessel_id=fake.random.choice(vessels).id
            ))
        VesselFlagMmsiHistory.objects.bulk_create(records, ignore_conflicts=True)

    def _generate_projects(self, count):
        """Generate Project records"""
        projects = []
        for i in range(count):
            projects.append(Project(
                code=f"PRJ{i:05d}",
                name=f"Project-{i}"
            ))
        Project.objects.bulk_create(projects, ignore_conflicts=True)

    def _generate_vessel_project_histories(self, count, projects, vessels, tasks):
        """Generate VesselProjectHistory records"""
        records = []
        created_triples = set()
        for i in range(count):
            try:
                project = fake.random.choice(projects)
                vessel = fake.random.choice(vessels)
                task = fake.random.choice(tasks)
                triple = (project.id, vessel.id, task.id)
                if triple not in created_triples:
                    records.append(VesselProjectHistory(
                        project_id=project.id,
                        vessel_id=vessel.id,
                        task_id=task.id,
                        rating=fake.random.randint(1, 5),
                        comment=fake.sentence()
                    ))
                    created_triples.add(triple)
            except:
                continue
        VesselProjectHistory.objects.bulk_create(records, ignore_conflicts=True)

