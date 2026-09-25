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
    current_stock = forms.IntegerField(
        required=False,
        initial=0,
        min_value=0,
        label="Current Stock",
        help_text="Opening quantity for the selected warehouse.",
    )
    current_stock_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(is_active=True),
        required=False,
        label="Stock Warehouse",
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
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            current_stock = self.instance.current_stock
            self.initial["current_stock"] = current_stock
            self.fields["current_stock"].initial = current_stock
            self.fields["current_stock"].disabled = True
            self.fields["current_stock"].help_text = (
                "Read-only total across all warehouses. Use Stock In/Out to change it."
            )
            self.fields.pop("current_stock_warehouse")

    def clean(self):
        cleaned_data = super().clean()
        current_stock = cleaned_data.get("current_stock") or 0
        warehouse = cleaned_data.get("current_stock_warehouse")
        if current_stock and not warehouse:
            self.add_error(
                "current_stock_warehouse",
                "Select a warehouse when entering current stock.",
            )
        return cleaned_data


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