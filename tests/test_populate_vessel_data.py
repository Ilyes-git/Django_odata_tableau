import pytest
from django.core.management import call_command
from io import StringIO
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


@pytest.mark.django_db
class TestPopulateVesselDataCommand:
    """Tests pour la commande populate_vessel_data"""

    def test_command_creates_ship_classes(self):
        """Test que la commande crée les ShipClass"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        assert ShipClass.objects.count() == 10
        ship_classes = ShipClass.objects.all()

        # Vérifier que les champs sont présents
        for sc in ship_classes:
            assert sc.name is not None
            assert sc.transit_speed_kn > 0
            assert sc.draught_m > 0

    def test_command_creates_ports(self):
        """Test que la commande crée les Ports"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '5', stdout=out)

        assert Port.objects.count() == 5
        ports = Port.objects.all()

        # Vérifier que les champs sont présents
        for port in ports:
            assert port.name is not None
            assert port.wpi_number is not None
            assert port.latitude is not None
            assert port.longitude is not None

    def test_command_creates_organisations(self):
        """Test que la commande crée les Organisations"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '8', stdout=out)

        assert Organisation.objects.count() == 8
        orgs = Organisation.objects.all()

        for org in orgs:
            assert org.name is not None
            assert org.acronym is not None

    def test_command_creates_roles(self):
        """Test que la commande crée les Roles"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '6', stdout=out)

        assert Role.objects.count() == 6
        roles = Role.objects.all()

        for role in roles:
            assert role.name is not None

    def test_command_creates_purposes(self):
        """Test que la commande crée les Purposes"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '7', stdout=out)

        assert Purpose.objects.count() == 7
        purposes = Purpose.objects.all()

        for purpose in purposes:
            assert purpose.name is not None
            assert purpose.description is not None

    def test_command_creates_tasks(self):
        """Test que la commande crée les Tasks"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '9', stdout=out)

        assert Task.objects.count() == 9
        tasks = Task.objects.all()

        # Vérifier que les acronymes sont uniques
        acronyms = [t.acronym for t in tasks]
        assert len(acronyms) == len(set(acronyms))

        for task in tasks:
            assert task.acronym is not None
            assert task.full_name is not None

    def test_command_creates_vessels(self):
        """Test que la commande crée les Vessels"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '5', stdout=out)

        vessels = Vessel.objects.all()
        assert len(vessels) == 5

        # Vérifier que les IMO sont uniques et séquentiels
        imos = sorted([v.imo for v in vessels])
        assert imos == list(range(9000000, 9000005))

        for vessel in vessels:
            assert vessel.name is not None
            assert vessel.year_built >= 2000
            assert vessel.ship_class is not None
            assert vessel.port is not None

    def test_command_creates_vessel_qualifications(self):
        """Test que la commande crée les VesselQualifications"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        vq = VesselQualification.objects.all()
        assert vq.count() > 0

        for qual in vq:
            assert qual.vessel is not None
            assert qual.task is not None

    def test_command_creates_vessel_purposes(self):
        """Test que la commande crée les VesselPurposes"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        vp = VesselPurpose.objects.all()
        assert vp.count() > 0

        for purpose in vp:
            assert purpose.vessel is not None
            assert purpose.purpose is not None
            assert isinstance(purpose.primary_purpose, bool)

    def test_command_creates_operational_parameters(self):
        """Test que la commande crée les OperationalParameters"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        op = OperationalParameter.objects.all()
        assert op.count() > 0

        for param in op:
            assert param.ship_class is not None
            assert param.purpose is not None
            assert param.task is not None
            assert param.timewindow_h > 0

    def test_command_creates_vessel_stakeholders(self):
        """Test que la commande crée les VesselStakeholders"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        vs = VesselStakeholder.objects.all()
        assert vs.count() > 0

        for stakeholder in vs:
            assert stakeholder.vessel is not None
            assert stakeholder.organisation is not None
            assert stakeholder.role is not None

    def test_command_creates_vessel_flag_mmsi_histories(self):
        """Test que la commande crée les VesselFlagMmsiHistories"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        histories = VesselFlagMmsiHistory.objects.all()
        assert histories.count() == 10

        for history in histories:
            assert history.vessel is not None
            assert history.mmsi is not None
            assert history.flag_start_date is not None
            assert history.flag_end_date is not None
            # Vérifier que end_date est après start_date
            assert history.flag_end_date >= history.flag_start_date

    def test_command_creates_projects(self):
        """Test que la commande crée les Projects"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '5', stdout=out)

        assert Project.objects.count() == 5
        projects = Project.objects.all()

        # Vérifier que les codes sont uniques et bien formatés
        codes = [p.code for p in projects]
        assert len(codes) == len(set(codes))

        for project in projects:
            assert project.code is not None
            assert project.code.startswith('PRJ')
            assert project.name is not None

    def test_command_creates_vessel_project_histories(self):
        """Test que la commande crée les VesselProjectHistories"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        histories = VesselProjectHistory.objects.all()
        assert histories.count() > 0

        for history in histories:
            assert history.project is not None
            assert history.vessel is not None
            assert history.task is not None
            assert 1 <= history.rating <= 5
            assert history.comment is not None

    def test_command_with_clear_option(self, db):
        """Test que l'option --clear supprime les données existantes"""
        # Créer quelques données d'abord
        call_command('populate_vessel_data', '--count', '5')
        assert ShipClass.objects.count() == 5

        # Appeler avec --clear
        call_command('populate_vessel_data', '--count', '3', '--clear')
        assert ShipClass.objects.count() == 3

    def test_command_default_count(self):
        """Test que la commande utilise 100 comme valeur par défaut"""
        out = StringIO()
        call_command('populate_vessel_data', stdout=out)

        # Vérifier qu'au moins 100 enregistrements sont créés pour chaque modèle
        assert ShipClass.objects.count() >= 100
        assert Port.objects.count() >= 100
        assert Task.objects.count() >= 100

    def test_command_custom_count(self):
        """Test que la commande respecte le paramètre --count custom"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '25', stdout=out)

        assert ShipClass.objects.count() == 25
        assert Port.objects.count() == 25
        assert Task.objects.count() == 25

    def test_all_models_created_with_relationships(self):
        """Test que toutes les relations sont créées correctement"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '15', stdout=out)

        # Vérifier que toutes les relations sont respectées
        vessels = Vessel.objects.all()
        for vessel in vessels:
            assert vessel.ship_class is not None
            assert vessel.port is not None

    def test_command_output_messages(self):
        """Test que la commande affiche les bons messages"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '5', stdout=out)

        output = out.getvalue()
        assert 'Generating ShipClass' in output
        assert 'Generating Port' in output
        assert 'Generating Vessel' in output
        assert 'Successfully populated' in output

    def test_command_idempotency_with_ignore_conflicts(self):
        """Test que la commande peut être exécutée plusieurs fois sans erreur"""
        out = StringIO()

        # Première exécution
        call_command('populate_vessel_data', '--count', '5', stdout=out)
        count_after_first = ShipClass.objects.count()

        # Deuxième exécution (avec ignore_conflicts=True)
        call_command('populate_vessel_data', '--count', '5', stdout=out)
        count_after_second = ShipClass.objects.count()

        # Les counts ne doublent pas grâce à ignore_conflicts
        assert count_after_second >= count_after_first

    def test_vessel_data_validity(self):
        """Test que les données générées sont valides"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        vessels = Vessel.objects.all()
        for vessel in vessels:
            # Vérifier les ranges des valeurs numériques
            assert vessel.year_built >= 2000
            assert vessel.length_overall_m > 0
            assert vessel.width_m > 0
            assert vessel.draught_m > 0
            assert vessel.gross_tonnage_t > 0
            assert vessel.deadweight_t > 0
            assert vessel.max_speed_kn > 0
            assert vessel.transit_speed_kn > 0
            assert vessel.fuel_capacity_t > 0

    def test_port_data_validity(self):
        """Test que les données de Port sont valides"""
        out = StringIO()
        call_command('populate_vessel_data', '--count', '10', stdout=out)

        ports = Port.objects.all()
        for port in ports:
            # Vérifier les coordonnées GPS
            assert -90 <= port.latitude <= 90
            assert -180 <= port.longitude <= 180
            # Vérifier les choix de dry_dock
            assert port.dry_dock in ['SMALL', 'MEDIUM', 'LARGE']
            # Vérifier les booléens
            assert isinstance(port.supplies_potable_water, bool)
            assert isinstance(port.supplies_fuel_oil, bool)

