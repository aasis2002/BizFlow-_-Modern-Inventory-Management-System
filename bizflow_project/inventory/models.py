# inventory/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Staff'),
        ('VIEWER', 'Viewer'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STAFF')
    phone = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    sku = models.CharField(max_length=50, unique=True)  # Stock Keeping Unit
    description = models.TextField(blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    current_stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    location = models.CharField(max_length=100, blank=True, null=True) # e.g., "Aisle 4, Shelf B"
    is_active = models.BooleanField(default=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return self.current_stock <= self.low_stock_threshold

class StockTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('IN', 'Stock In (Purchase)'),
        ('OUT', 'Stock Out (Sale)'),
        ('ADJ', 'Adjustment'),
        ('RET', 'Return to Supplier'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    note = models.CharField(max_length=255, blank=True, null=True) # e.g., "PO #123", "Sale to Kumar Store"
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) # Who performed the action

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.product.name} - Qty: {self.quantity}"
    
class Customer(models.Model):
    CUSTOMER_TYPES = (
        ('RETAIL', 'Retail Customer'),
        ('WHOLESALE', 'Wholesale Customer'),
        ('BUSINESS', 'Business Client'),
    )
    
    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='RETAIL')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    tax_number = models.CharField(max_length=50, blank=True, null=True)  # VAT/PAN number
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_customer_type_display()})"

    class Meta:
        ordering = ['name']