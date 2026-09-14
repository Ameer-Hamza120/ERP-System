from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group, Permission
from .models import CompanySettings, DocumentSequence


class UserCreateForm(UserCreationForm):
    """
    Form for creating a new user with role assignment.
    """

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    is_active = forms.BooleanField(initial=True, required=False)
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Role",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
            "is_active",
            "group",
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.is_active = self.cleaned_data["is_active"]
        if commit:
            user.save()
            group = self.cleaned_data["group"]
            user.groups.clear()
            user.groups.add(group)
        return user


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating an existing user.
    """

    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Role",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["group"].initial = self.instance.groups.first()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            user.groups.clear()
            user.groups.add(self.cleaned_data["group"])
        return user


class RoleForm(forms.ModelForm):
    """
    Form for creating/editing a role (group) and assigning permissions.
    """

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by(
            "content_type__app_label", "codename"
        ),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["permissions"].initial = self.instance.permissions.all()

    def save(self, commit=True):
        group = super().save(commit=False)
        if commit:
            group.save()
            group.permissions.set(self.cleaned_data["permissions"])
        return group


class CompanySettingsForm(forms.ModelForm):
    """
    Form for editing company settings.
    """

    class Meta:
        model = CompanySettings
        fields = "__all__"


class DocumentSequenceForm(forms.ModelForm):
    class Meta:
        model = DocumentSequence
        fields = ["document_type", "prefix", "include_year", "next_number", "padding"]
        widgets = {
            "next_number": forms.NumberInput(attrs={"min": 1}),
            "padding": forms.NumberInput(attrs={"min": 1, "max": 12}),
        }
