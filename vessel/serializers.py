from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.serializers import ALL_FIELDS
from .models import (
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


class ShipClassSerializer(FlexFieldsModelSerializer):
    """Serializer pour ShipClass avec support $expand"""
    class Meta:
        model = ShipClass
        fields = ALL_FIELDS


class PortSerializer(FlexFieldsModelSerializer):
    """Serializer pour Port avec support $expand"""
    class Meta:
        model = Port
        fields = ALL_FIELDS


class OrganisationSerializer(FlexFieldsModelSerializer):
    """Serializer pour Organisation avec support $expand"""
    class Meta:
        model = Organisation
        fields = ALL_FIELDS


class RoleSerializer(FlexFieldsModelSerializer):
    """Serializer pour Role avec support $expand"""
    class Meta:
        model = Role
        fields = ALL_FIELDS


class PurposeSerializer(FlexFieldsModelSerializer):
    """Serializer pour Purpose avec support $expand"""
    class Meta:
        model = Purpose
        fields = ALL_FIELDS


class TaskSerializer(FlexFieldsModelSerializer):
    """Serializer pour Task avec support $expand"""
    class Meta:
        model = Task
        fields = ALL_FIELDS


class VesselSerializer(FlexFieldsModelSerializer):
    """Serializer pour Vessel avec support $expand"""
    class Meta:
        model = Vessel
        fields = ALL_FIELDS
        expandable_fields = {
            'ship_class': ('vessel.serializers.ShipClassSerializer', {}),
            'port': ('vessel.serializers.PortSerializer', {}),
        }


class VesselQualificationSerializer(FlexFieldsModelSerializer):
    """Serializer pour VesselQualification avec support $expand"""
    class Meta:
        model = VesselQualification
        fields = ALL_FIELDS
        expandable_fields = {
            'vessel': ('vessel.serializers.VesselSerializer', {}),
            'task': ('vessel.serializers.TaskSerializer', {}),
        }


class VesselPurposeSerializer(FlexFieldsModelSerializer):
    """Serializer pour VesselPurpose avec support $expand"""
    class Meta:
        model = VesselPurpose
        fields = ALL_FIELDS
        expandable_fields = {
            'vessel': ('vessel.serializers.VesselSerializer', {}),
            'purpose': ('vessel.serializers.PurposeSerializer', {}),
        }


class OperationalParameterSerializer(FlexFieldsModelSerializer):
    """Serializer pour OperationalParameter avec support $expand"""
    class Meta:
        model = OperationalParameter
        fields = ALL_FIELDS
        expandable_fields = {
            'ship_class': ('vessel.serializers.ShipClassSerializer', {}),
            'purpose': ('vessel.serializers.PurposeSerializer', {}),
            'task': ('vessel.serializers.TaskSerializer', {}),
        }


class VesselStakeholderSerializer(FlexFieldsModelSerializer):
    """Serializer pour VesselStakeholder avec support $expand"""
    class Meta:
        model = VesselStakeholder
        fields = ALL_FIELDS
        expandable_fields = {
            'organisation': ('vessel.serializers.OrganisationSerializer', {}),
            'role': ('vessel.serializers.RoleSerializer', {}),
            'vessel': ('vessel.serializers.VesselSerializer', {}),
        }


class VesselFlagMmsiHistorySerializer(FlexFieldsModelSerializer):
    """Serializer pour VesselFlagMmsiHistory avec support $expand"""
    class Meta:
        model = VesselFlagMmsiHistory
        fields = ALL_FIELDS
        expandable_fields = {
            'vessel': ('vessel.serializers.VesselSerializer', {}),
        }


class ProjectSerializer(FlexFieldsModelSerializer):
    """Serializer pour Project avec support $expand"""
    class Meta:
        model = Project
        fields = ALL_FIELDS


class VesselProjectHistorySerializer(FlexFieldsModelSerializer):
    """Serializer pour VesselProjectHistory avec support $expand"""
    class Meta:
        model = VesselProjectHistory
        fields = ALL_FIELDS
        expandable_fields = {
            'project': ('vessel.serializers.ProjectSerializer', {}),
            'vessel': ('vessel.serializers.VesselSerializer', {}),
            'task': ('vessel.serializers.TaskSerializer', {}),
        }

