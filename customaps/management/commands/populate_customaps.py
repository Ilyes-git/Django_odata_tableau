from django.core.management.base import BaseCommand
from faker import Faker
from customaps.models import Folder, Map


class Command(BaseCommand):
    help = 'Populate Folder and Map models with fake data using Faker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--folders',
            type=int,
            default=5,
            help='Number of root folders to create (default: 5)',
        )
        parser.add_argument(
            '--depth',
            type=int,
            default=3,
            help='Depth of folder hierarchy (default: 3)',
        )
        parser.add_argument(
            '--maps',
            type=int,
            default=3,
            help='Number of maps to create per folder (default: 3)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing Folder and Map records before populating',
        )

    def handle(self, *args, **options):
        fake = Faker()
        num_root_folders = options['folders']
        depth = options['depth']
        num_maps_per_folder = options['maps']
        clear_data = options['clear']

        # Clear existing data if requested
        if clear_data:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Folder.objects.all().delete()
            Map.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Data cleared.'))

        self.stdout.write(f'Creating {num_root_folders} root folders with depth {depth} and {num_maps_per_folder} maps per folder...')

        users = [fake.user_name() for _ in range(3)]

        # Create root folders and their children recursively
        root_folders = []
        for i in range(num_root_folders):
            folder = Folder.objects.create(
                name=f'{fake.word()}_root_{i+1}',
                parent=None,
                username=fake.random_element(users),
            )
            root_folders.append(folder)
            self.stdout.write(f'✓ Created root folder: {folder.name}')

            # Create maps for root folder
            self._create_maps_for_folder(folder, num_maps_per_folder, fake)

            # Create nested subfolders
            self._create_nested_folders(folder, depth - 1, 0, num_maps_per_folder, users, fake)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created folder hierarchy with recursion!'
            )
        )

    def _create_nested_folders(self, parent_folder, remaining_depth, current_depth, num_maps_per_folder, users, fake):
        """Recursively create nested folders"""
        if remaining_depth <= 0:
            return

        # Create 2-3 subfolders per folder
        num_subfolders = fake.random_int(min=2, max=3)
        for i in range(num_subfolders):
            subfolder = Folder.objects.create(
                name=f'{fake.word()}_lvl{current_depth+2}_{i+1}',
                parent=parent_folder,
                username=parent_folder.username,
            )
            self.stdout.write(f'  {"  " * current_depth}└─ Created subfolder: {subfolder.name}')

            # Create maps for this subfolder
            self._create_maps_for_folder(subfolder, num_maps_per_folder, fake)

            # Recursively create deeper subfolders
            self._create_nested_folders(subfolder, remaining_depth - 1, current_depth + 1, num_maps_per_folder, users, fake)

    def _create_maps_for_folder(self, folder, num_maps, fake):
        """Create maps for a given folder"""
        for j in range(num_maps):
            map_data = {
                'type': 'FeatureCollection',
                'features': [
                    {
                        'type': 'Feature',
                        'properties': {
                            'name': fake.city(),
                            'description': fake.sentence(),
                        },
                        'geometry': {
                            'type': 'Point',
                            'coordinates': [float(fake.longitude()), float(fake.latitude())],
                        },
                    }
                ],
            }

            map_obj = Map.objects.create(
                name=f'{fake.word()}_{j+1}',
                data=map_data,
                folder=folder,
                username=folder.username,
            )
            self.stdout.write(f'    ├─ map: {map_obj.name}')

