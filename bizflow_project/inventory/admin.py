# inventory/admin.py

from django.contrib import admin
from .models import Category, Customer, Supplier, Product, StockTransaction, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'department')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_editable = ('role',)

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description') # Columns to display in the list view
    search_fields = ('name',) # Adds a search box to filter by name

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    list_filter = ('name',) # Adds a filter sidebar
    search_fields = ('name', 'contact_person')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'current_stock', 'unit_price', 'is_active')
    list_filter = ('category', 'is_active') # Filter by category and active status
    search_fields = ('name', 'sku') # Search by product name or SKU
    # This makes editing products in the list view much easier
    list_editable = ('current_stock', 'unit_price', 'is_active')

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('product', 'transaction_type', 'quantity', 'user', 'timestamp')
    list_filter = ('transaction_type', 'timestamp')
    readonly_fields = ('timestamp',) # Prevents editing of the timestamp

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'customer_type', 'phone', 'email', 'credit_limit', 'current_balance', 'is_active')
    list_filter = ('customer_type', 'is_active')
    search_fields = ('name', 'company_name', 'phone', 'email')
    list_editable = ('is_active',)