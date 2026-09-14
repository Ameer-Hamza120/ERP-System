from django import forms
from .models import ItemGroup, Item, Warehouse, StockTransfer


class ItemGroupForm(forms.ModelForm):
    class Meta:
        model = ItemGroup
        fields = ["name", "description", "is_active"]


class ItemForm(forms.ModelForm):
    item_code = forms.CharField(
        required=False,
        label="Item Code",
        help_text="Leave blank to auto-generate.",
    )

    class Meta:
        model = Item
        fields = [
            "item_code",
            "name",
            "sku",
            "barcode",
            "group",
            "description",
            "unit_of_measure",
            "purchase_price",
            "selling_price",
            "tax_percent",
            "minimum_stock_level",
            "maximum_stock_level",
            "reorder_level",
            "image",
            "is_active",
        ]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            "code",
            "name",
            "location",
            "address",
            "city",
            "country",
            "manager",
            "description",
            "is_active",
        ]


class StockInForm(forms.Form):
    """
    Form for receiving stock into a warehouse.
    """

    item = forms.ModelChoiceField(queryset=Item.objects.filter(is_active=True))
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True)
    )
    quantity = forms.IntegerField(min_value=1)


class StockOutForm(forms.Form):
    """
    Form for issuing stock from a warehouse.
    """

    item = forms.ModelChoiceField(queryset=Item.objects.filter(is_active=True))
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True)
    )
    quantity = forms.IntegerField(min_value=1)


class StockTransferForm(forms.ModelForm):
    class Meta:
        model = StockTransfer
        fields = [
            "item",
            "from_warehouse",
            "to_warehouse",
            "quantity",
            "transfer_date",
            "notes",
        ]
        widgets = {
            "transfer_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        from_wh = cleaned_data.get("from_warehouse")
        to_wh = cleaned_data.get("to_warehouse")
        if from_wh and to_wh and from_wh == to_wh:
            raise forms.ValidationError(
                "Source and destination warehouses cannot be the same."
            )
        return cleaned_data