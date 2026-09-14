from django.contrib.auth.models import User, Group, Permission
from rest_framework import serializers

from .models import CompanySettings, DocumentSequence


class PermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.StringRelatedField()

    class Meta:
        model = Permission
        fields = ["id", "codename", "name", "content_type"]


class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )
    permissions_detail = PermissionSerializer(
        source="permissions", many=True, read_only=True
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions", "permissions_detail"]


class UserSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False, write_only=True
    )
    groups = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "date_joined",
            "group",
            "groups",
        ]
        read_only_fields = ["last_login", "date_joined", "is_superuser"]

    def create(self, validated_data):
        group = validated_data.pop("group", None)
        user = User.objects.create_user(**validated_data)
        if group:
            user.groups.set([group])
        return user

    def update(self, instance, validated_data):
        group = validated_data.pop("group", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if group is not None:
            instance.groups.set([group])
        return instance


class UserCreateSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        group = validated_data.pop("group", None)
        user = User.objects.create_user(password=password, **validated_data)
        if group:
            user.groups.set([group])
        return user


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = "__all__"


class DocumentSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentSequence
        fields = "__all__"
        read_only_fields = ["last_number"]


class MeSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_superuser",
            "last_login",
            "groups",
            "permissions",
        ]

    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions())