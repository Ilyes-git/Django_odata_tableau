from django.db import models
from datetime import date

# Generic default value for some attributes in the model
generic_default_value = "UNDEFINED"


class ShipClass(models.Model):
    id = models.BigAutoField(primary_key=True)
    # class_name's domain values: BID AVERAGE, GENERIC, GENERIC II, ILE DE CLASSE
    name = models.CharField(max_length=25, unique=True, null=False, blank=False)
    transit_speed_kn = models.FloatField(null=False, blank=True)
    draught_m = models.FloatField(null=False, blank=True)



class Port(models.Model):
    id = models.BigAutoField(primary_key=True)
    wpi_number = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=40, null=False, default=generic_default_value)
    un_locode = models.CharField(max_length=10, null=True, blank=True)
    world_water_body = models.TextField(null=True, blank=True)
    tidal_range_m = models.FloatField(null=True, blank=True)
    entrance_width_m = models.FloatField(null=True, blank=True)
    anchorage_depth_m = models.FloatField(null=True, blank=True)
    oil_terminal_depth_m = models.FloatField(null=True, blank=True)
    maximum_vessel_length_m = models.FloatField(null=True, blank=True)
    maximum_vessel_draft_m = models.FloatField(null=True, blank=True)
    supplies_potable_water = models.BooleanField(null=True, default=False)
    supplies_fuel_oil = models.BooleanField(null=True, default=False)

    class DryDock(models.TextChoices):
        SMALL = "SMALL", "SMALL"
        MEDIUM = "MEDIUM", "MEDIUM"
        LARGE = "LARGE", "LARGE"

    dry_dock = models.CharField(
        max_length=15, choices=DryDock.choices, null=True, default=DryDock.MEDIUM
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)




class Organisation(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.TextField(unique=True, null=False, blank=True)
    acronym = models.CharField(max_length=30, null=True, blank=True)
    address = models.TextField(null=True, blank=True)




class Role(models.Model):
    id = models.BigAutoField(primary_key=True)
    # label's domain values: MANAGER, OWNER, BUILDER, SUPPLIER, AGENT
    name = models.CharField(max_length=10, unique=True, null=False, blank=True)



class Purpose(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=20, unique=True, null=False, blank=True)
    description = models.TextField(unique=True, null=True, blank=True)



class Task(models.Model):
    id = models.BigAutoField(primary_key=True)
    acronym = models.CharField(max_length=10, unique=True, null=False, blank=False)
    full_name = models.CharField(max_length=30, unique=True, null=True, blank=True)
    description = models.TextField(unique=True, null=True, blank=True)




class Vessel(models.Model):
    id = models.BigAutoField(primary_key=True)
    imo = models.IntegerField(unique=True, null=True, blank=True)
    name = models.TextField(unique=True, null=True, blank=True)
    acronym = models.CharField(max_length=20, null=True, blank=True)
    main_lay = models.BooleanField(null=True, default=False)
    dynamic_positioning = models.CharField(max_length=20, null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)
    length_overall_m = models.FloatField(null=True, blank=True)
    width_m = models.FloatField(null=True, blank=True)
    draught_m = models.FloatField(null=True, blank=True)
    gross_tonnage_t = models.FloatField(null=True, blank=True)
    deadweight_t = models.FloatField(null=True, blank=True)
    max_speed_kn = models.FloatField(null=True, blank=True)
    transit_speed_kn = models.FloatField(null=True, blank=True)
    fuel_capacity_t = models.FloatField(null=True, blank=True)
    fuel_safety_level_t = models.FloatField(null=True, blank=True)


    ship_class = models.ForeignKey(
        "ShipClass", on_delete=models.DO_NOTHING, null=True, blank=True
    )
    port = models.ForeignKey("Port", on_delete=models.DO_NOTHING, null=True, blank=True)



# VesselQualification is a Class Asso allowing to handle the multiple activities (Task)
# a Vessel might be qualified for.


class VesselQualification(models.Model):
    id = models.BigAutoField(primary_key=True)

    # <fk> statement
    vessel = models.ForeignKey("Vessel", on_delete=models.CASCADE)
    task = models.ForeignKey("Task", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("vessel_id", "task_id")


# VesselPurpose is a Class Asso allowing to handle the multiple purposes (Purpose)
# a Vessel might be intended for. It also characterises as primary or not these
# purposes.


class VesselPurpose(models.Model):
    id = models.BigAutoField(primary_key=True)
    primary_purpose = models.BooleanField(null=False, blank=True)

    # <fk> statement
    vessel = models.ForeignKey("Vessel", on_delete=models.CASCADE)
    purpose = models.ForeignKey("Purpose", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("vessel_id", "purpose_id")


# OperationalParameter is a Class Asso allowing to define, for each unique set of vessel class-purpose-task
# (ShipClass-Purpose-Task), its corresponding set of operational parameters.


class OperationalParameter(models.Model):
    id = models.BigAutoField(primary_key=True)
    timewindow_h = models.IntegerField(null=True, blank=True)
    max_wind_speed_kn = models.FloatField(null=True, blank=True)
    max_wave_m = models.FloatField(null=True, blank=True)
    max_current_kn = models.FloatField(null=True, blank=True)
    # The need for the three attributes below has to be confirmed (yet implemented).
    standard_consumption = models.IntegerField(null=True, blank=True)
    theoretical_speed_kn = models.IntegerField(null=True, blank=True)
    applicable_speed_kn = models.IntegerField(null=True, blank=True)

    ship_class = models.ForeignKey("ShipClass", on_delete=models.DO_NOTHING, related_name="operational_parameters")
    purpose = models.ForeignKey("Purpose", on_delete=models.DO_NOTHING)
    task = models.ForeignKey("Task", on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = ("ship_class_id", "purpose_id", "task_id")


# VesselStakeholder is a Class Asso allowing to record the various roles organisations
# might handle regarding the vessels, whether they supply, manage, or own them.


class VesselStakeholder(models.Model):
    id = models.BigAutoField(primary_key=True)

    # <fk> statement
    organisation = models.ForeignKey("Organisation", on_delete=models.CASCADE)
    role = models.ForeignKey("Role", on_delete=models.CASCADE)
    vessel = models.ForeignKey("Vessel", on_delete=models.CASCADE)

    class Meta:

        unique_together = ("organisation_id", "role_id", "vessel_id")


# Vessel_Flag_Mmsi_History is a Class Asso allowing to store and historise the MMSI of the vessels.


class VesselFlagMmsiHistory(models.Model):
    id = models.BigAutoField(primary_key=True)

    flag_start_date = models.DateField(null=True, blank=False)
    flag_end_date = models.DateField(null=True, default=date.today)
    mmsi = models.IntegerField(null=True, blank=True)

    # REAL CONDITIONS

    vessel = models.ForeignKey("Vessel", on_delete=models.DO_NOTHING)

    class Meta:

        unique_together = (
            "mmsi",
            "vessel_id",
            "flag_start_date",
        )


# Project table represents a gateway to future connections to the projects features,
# outside the vessel DB.


class Project(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=5, null=False, blank=True)
    name = models.TextField(null=True, blank=True)



# Vessel_Vessel_History is a Class Asso allowing to track the task performed by a vessel in
# the context of a specific project. It also allows to record a comment and a rating regarding the
# performance of the vessel during this task.


class VesselProjectHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    rating = models.IntegerField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    # <fk> statement
    project = models.ForeignKey("Project", on_delete=models.DO_NOTHING)
    vessel = models.ForeignKey("Vessel", on_delete=models.DO_NOTHING)
    task = models.ForeignKey("Task", on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = ("project_id", "vessel_id", "task_id")
