from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    # Admin Dashboard
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    
    # Admin Authentication
    path('admin/login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='admin_login'),
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='admin_login'), name='admin_logout'),
    
    # Regular application URLs
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/add/', views.add_product, name='add_product'),
    path('product/edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('product/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('stock/update/', views.add_stock_transaction, name='add_stock_transaction'),
    
    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('supplier/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('supplier/add/', views.add_supplier, name='add_supplier'),
    path('supplier/edit/<int:pk>/', views.edit_supplier, name='edit_supplier'),
    path('supplier/delete/<int:pk>/', views.delete_supplier, name='delete_supplier'),
    
    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customer/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customer/add/', views.add_customer, name='add_customer'),
    path('customer/edit/<int:pk>/', views.edit_customer, name='edit_customer'),
    path('customer/delete/<int:pk>/', views.delete_customer, name='delete_customer'),
    
    # Reports
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # PDF Reports
    path('reports/pdf/stock/', views.generate_stock_report_pdf, name='generate_inventory_pdf'),
    path('reports/pdf/low-stock/', views.generate_low_stock_report_pdf, name='generate_low_stock_pdf'),
    path('reports/pdf/supplier/', views.generate_supplier_report_pdf, name='generate_supplier_pdf'),
    
    # CSV Reports
    path('reports/csv/stock/', views.generate_stock_report_csv, name='generate_stock_csv'),
    path('reports/csv/low-stock/', views.generate_low_stock_report_csv, name='generate_low_stock_csv'),
    path('reports/csv/supplier/', views.generate_supplier_report_csv, name='generate_supplier_csv'),
]