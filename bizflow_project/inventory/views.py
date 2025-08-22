# inventory/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse
import csv
import datetime
import json
from datetime import datetime, timedelta
# PDF imports
import datetime
from django.contrib.auth.decorators import user_passes_test
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
from .models import Product, Category, Supplier, StockTransaction, Customer
from .forms import ProductForm, StockTransactionForm, CustomerForm, SupplierForm
from django.shortcuts import redirect


@login_required
def dashboard(request):
    # Basic stats
    total_products = Product.objects.filter(is_active=True).count()
    total_inventory_value = Product.objects.filter(is_active=True).aggregate(
        total_value=Sum(models.F('current_stock') * models.F('cost_price'))
    )['total_value'] or 0
    
    low_stock_count = Product.objects.filter(
        is_active=True, 
        current_stock__lte=models.F('low_stock_threshold')
    ).count()
    
    total_customers = Customer.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.count()
    
    # Recent activity
    recent_transactions = StockTransaction.objects.select_related('product', 'user').order_by('-timestamp')[:5]
    low_stock_products = Product.objects.filter(
        is_active=True, 
        current_stock__lte=models.F('low_stock_threshold')
    )[:5]
    
    # Category distribution for chart
    categories = Category.objects.annotate(
        product_count=Count('product'),
        category_value=Sum(models.F('product__current_stock') * models.F('product__cost_price'))
    )
    
    # Monthly transaction data for chart
    today = timezone.now()
    monthly_data = []
    for i in range(6):
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        
        month_transactions = StockTransaction.objects.filter(
            timestamp__gte=month_start,
            timestamp__lt=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%b %Y'),
            'transactions': month_transactions
        })
    
    monthly_data.reverse()

    # Stock status for chart
    stock_status = {
        'healthy': Product.objects.filter(
            is_active=True, 
            current_stock__gt=models.F('low_stock_threshold')
        ).count(),
        'low': low_stock_count,
        'out_of_stock': Product.objects.filter(
            is_active=True, 
            current_stock=0
        ).count()
    }
    
    context = {
        'total_products': total_products,
        'total_inventory_value': total_inventory_value,
        'low_stock_count': low_stock_count,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'recent_transactions': recent_transactions,
        'low_stock_products': low_stock_products,
        'categories': categories,
        'monthly_data': monthly_data,
        'stock_status': stock_status,
        'monthly_data_json': json.dumps(monthly_data),
        'stock_status_json': json.dumps(stock_status),
    }
    return render(request, 'inventory/dashboard.html', context)

# Supplier CRUD Views
@login_required
def add_supplier(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" added successfully!')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    
    context = {'form': form, 'title': 'Add New Supplier'}
    return render(request, 'inventory/generic_form.html', context)

@login_required
def edit_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" updated successfully!')
            return redirect('supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    
    context = {'form': form, 'title': f'Edit Supplier: {supplier.name}'}
    return render(request, 'inventory/generic_form.html', context)

@login_required
def delete_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'Supplier "{supplier_name}" deleted successfully!')
        return redirect('supplier_list')
    
    context = {'object': supplier, 'object_type': 'supplier'}
    return render(request, 'inventory/confirm_delete.html', context)

@login_required
def product_list(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    low_stock = request.GET.get('low_stock')

    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query))
    if category_id and category_id != 'all':
        products = products.filter(category_id=category_id)
    if low_stock:
        products = products.filter(current_stock__lte=models.F('low_stock_threshold'))

    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories,
        'current_query': query,
        'current_category': category_id,
        'current_low_stock': low_stock,
    }
    return render(request, 'inventory/product_list.html', context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category', 'supplier'), pk=pk)
    transactions = StockTransaction.objects.filter(product=product).select_related('user').order_by('-timestamp')[:10]
    
    context = {
        'product': product,
        'transactions': transactions
    }
    return render(request, 'inventory/product_detail.html', context)

# Product CRUD Views
@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('product_list')
    else:
        form = ProductForm()
    
    context = {'form': form, 'title': 'Add New Product'}
    return render(request, 'inventory/generic_form.html', context)

@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    
    context = {'form': form, 'title': f'Edit Product: {product.name}'}
    return render(request, 'inventory/generic_form.html', context)

@login_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('product_list')
    
    context = {'object': product, 'object_type': 'product'}
    return render(request, 'inventory/confirm_delete.html', context)

@login_required
def add_stock_transaction(request):
    # Check if a specific product was requested via the URL (e.g., ?product=2)
    product_id = request.GET.get('product')
    initial_data = {}
    if product_id:
        # If a product ID is provided, try to get the product and pre-fill the form
        try:
            product = Product.objects.get(id=product_id)
            initial_data['product'] = product
        except Product.DoesNotExist:
            # If the product doesn't exist, just ignore and show an empty form
            pass

    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user

            product = transaction.product
            old_stock = product.current_stock

            # Update product stock based on transaction type
            if transaction.transaction_type == 'IN':
                product.current_stock += transaction.quantity
            elif transaction.transaction_type == 'OUT':
                product.current_stock -= transaction.quantity
            elif transaction.transaction_type == 'ADJ':
                product.current_stock += transaction.quantity
            elif transaction.transaction_type == 'RET':
                product.current_stock -= transaction.quantity

            product.save()
            transaction.save()

            messages.success(request, f'Stock updated for {product.name}. Old: {old_stock}, New: {product.current_stock}')
            return redirect('product_detail', pk=product.pk)
    else:
        # On a GET request, create the form with the initial data (pre-selected product)
        form = StockTransactionForm(initial=initial_data)

    context = {'form': form, 'title': 'Update Stock'}
    return render(request, 'inventory/generic_form.html', context)

# Customer Views
@login_required
def customer_list(request):
    customers = Customer.objects.filter(is_active=True).order_by('name')
    return render(request, 'inventory/customer_list.html', {'customers': customers})

@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'inventory/customer_detail.html', {'customer': customer})

@login_required
def add_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" added successfully!')
            return redirect('customer_list')
    else:
        form = CustomerForm()
    
    context = {'form': form, 'title': 'Add New Customer'}
    return render(request, 'inventory/generic_form.html', context)

@login_required
def edit_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" updated successfully!')
            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    context = {'form': form, 'title': f'Edit Customer: {customer.name}'}
    return render(request, 'inventory/generic_form.html', context)

@login_required
def delete_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer_name = customer.name
        customer.delete()
        messages.success(request, f'Customer "{customer_name}" deleted successfully!')
        return redirect('customer_list')
    
    context = {'object': customer, 'object_type': 'customer'}
    return render(request, 'inventory/confirm_delete.html', context)

# Supplier Views
@login_required
def supplier_list(request):
    suppliers = Supplier.objects.all().annotate(
        product_count=Count('product'),
        total_inventory_value=Sum(models.F('product__current_stock') * models.F('product__cost_price'))
    )
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    products = Product.objects.filter(supplier=supplier, is_active=True)
    
    # Calculate supplier statistics
    total_products = products.count()
    total_stock_value = sum(product.current_stock * product.cost_price for product in products)
    low_stock_products = products.filter(current_stock__lte=models.F('low_stock_threshold')).count()
    
    context = {
        'supplier': supplier,
        'products': products,
        'total_products': total_products,
        'total_stock_value': total_stock_value,
        'low_stock_products': low_stock_products,
    }
    return render(request, 'inventory/supplier_detail.html', context)

# CSV Report Functions
def generate_stock_report_csv(request):
    """Generate CSV stock report"""
    response = HttpResponse(
        content_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="bizflow_stock_report.csv"'},
    )
    
    # Force UTF-8 BOM for Excel compatibility
    response.write('\ufeff')
    
    writer = csv.writer(response)
    # Write header
    writer.writerow(['BizFlow - Inventory Stock Report'])
    writer.writerow([f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])
    writer.writerow(['Product Name', 'SKU', 'Category', 'Current Stock', 'Low Stock Threshold', 'Status', 'Cost Price', 'Selling Price', 'Stock Value'])
    
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')
    
    for product in products:
        status = "LOW STOCK" if product.current_stock <= product.low_stock_threshold else "OK"
        stock_value = product.current_stock * product.cost_price
        
        writer.writerow([
            product.name,
            product.sku,
            product.category.name if product.category else 'N/A',
            product.current_stock,
            product.low_stock_threshold,
            status,
            float(product.cost_price),
            float(product.unit_price),
            float(stock_value)
        ])
    
    # Add summary
    writer.writerow([])
    total_value = sum(product.current_stock * product.cost_price for product in products)
    writer.writerow(['TOTAL INVENTORY VALUE:', '', '', '', '', '', '', '', float(total_value)])
    
    return response

def generate_low_stock_report_csv(request):
    """Generate CSV low stock report"""
    response = HttpResponse(
        content_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="bizflow_low_stock_alert.csv"'},
    )
    
    # Force UTF-8 BOM for Excel compatibility
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['BizFlow - Low Stock Alert Report'])
    writer.writerow([f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])
    writer.writerow(['Product Name', 'SKU', 'Current Stock', 'Threshold', 'Shortage', 'Urgency Level', 'Category', 'Cost Price', 'Required Investment'])
    
    low_stock_products = Product.objects.filter(
        is_active=True, 
        current_stock__lte=models.F('low_stock_threshold')
    ).select_related('category')
    
    for product in low_stock_products:
        shortage = product.low_stock_threshold - product.current_stock
        required_investment = shortage * product.cost_price
        
        if product.current_stock == 0:
            urgency = "CRITICAL (OUT OF STOCK)"
        elif shortage >= 10:
            urgency = "VERY HIGH"
        elif shortage >= 5:
            urgency = "HIGH"
        else:
            urgency = "MEDIUM"
        
        writer.writerow([
            product.name,
            product.sku,
            product.current_stock,
            product.low_stock_threshold,
            shortage,
            urgency,
            product.category.name if product.category else 'N/A',
            float(product.cost_price),
            float(required_investment)
        ])
    
    return response

def generate_supplier_report_csv(request):
    """Generate CSV supplier report"""
    response = HttpResponse(
        content_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="bizflow_supplier_report.csv"'},
    )
    
    # Force UTF-8 BOM for Excel compatibility
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['BizFlow - Supplier Performance Report'])
    writer.writerow([f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'])
    writer.writerow([])
    writer.writerow(['Supplier Name', 'Contact Person', 'Email', 'Phone', 'Total Products', 'Total Inventory Value', 'Address', 'Performance Rating'])
    
    suppliers = Supplier.objects.all().annotate(
        product_count=Count('product'),
        total_value=Sum(models.F('product__current_stock') * models.F('product__cost_price'))
    )
    
    for supplier in suppliers:
        # Simple performance rating
        total_val = supplier.total_value or 0
        if total_val > 100000:
            rating = "Excellent (5 Stars)"
        elif total_val > 50000:
            rating = "Good (4 Stars)"
        elif total_val > 10000:
            rating = "Average (3 Stars)"
        elif supplier.product_count > 0:
            rating = "Needs Attention (2 Stars)"
        else:
            rating = "No Products (1 Star)"
        
        writer.writerow([
            supplier.name,
            supplier.contact_person or 'N/A',
            supplier.email or 'N/A',
            supplier.phone or 'N/A',
            supplier.product_count,
            float(total_val),
            supplier.address or 'N/A',
            rating
        ])
    
    return response

# PDF Report Functions (Using ReportLab - More Reliable)
def generate_stock_report_pdf(request):
    """Generate PDF stock report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1,
        textColor=colors.darkblue
    )
    
    # Header
    elements.append(Paragraph("BizFlow Inventory Management", styles['Title']))
    elements.append(Paragraph("Stock Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Get data
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')
    
    # Prepare table data
    table_data = [
        ['Product', 'SKU', 'Category', 'Stock', 'Threshold', 'Status', 'Cost', 'Price']
    ]
    
    for product in products:
        status = "LOW" if product.current_stock <= product.low_stock_threshold else "OK"
        table_data.append([
            product.name[:20] + '...' if len(product.name) > 20 else product.name,
            product.sku,
            product.category.name[:15] + '...' if product.category and len(product.category.name) > 15 else (product.category.name if product.category else '-'),
            str(product.current_stock),
            str(product.low_stock_threshold),
            status,
            f"रु{product.cost_price:.0f}",
            f"रु{product.unit_price:.0f}"
        ])
    
    # Create table
    table = Table(table_data, colWidths=[3*cm, 2*cm, 2.5*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DEE2E6')),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Summary
    total_value = sum(product.current_stock * product.cost_price for product in products)
    low_stock_count = sum(1 for product in products if product.current_stock <= product.low_stock_threshold)
    
    summary_data = [
        ['Total Products', 'Total Value', 'Low Stock Items', 'Report Date'],
        [str(len(products)), f"रु {total_value:,.2f}", str(low_stock_count), datetime.datetime.now().strftime('%Y-%m-%d')]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*cm, 4*cm, 3*cm, 3*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#E9ECEF')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DEE2E6')),
    ]))
    
    elements.append(summary_table)
    
    # Footer
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Generated by BizFlow Inventory System - Biratnagar, Nepal", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bizflow_stock_report.pdf"'
    return response

def generate_low_stock_report_pdf(request):
    """Generate PDF low stock report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("BizFlow Inventory Management", styles['Title']))
    elements.append(Paragraph("LOW STOCK ALERT REPORT", 
                            ParagraphStyle('AlertTitle', parent=styles['Heading1'], fontSize=16, textColor=colors.red, alignment=1)))
    elements.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    low_stock_products = Product.objects.filter(
        is_active=True, 
        current_stock__lte=models.F('low_stock_threshold')
    ).select_related('category')
    
    if low_stock_products:
        table_data = [['Product', 'SKU', 'Current', 'Threshold', 'Shortage', 'Urgency', 'Action Needed']]
        
        for product in low_stock_products:
            shortage = product.low_stock_threshold - product.current_stock
            
            if product.current_stock == 0:
                urgency = "CRITICAL"
                action = "IMMEDIATE RESTOCK"
            elif shortage >= 10:
                urgency = "HIGH"
                action = "URGENT ORDER"
            elif shortage >= 5:
                urgency = "MEDIUM"
                action = "PLAN ORDER"
            else:
                urgency = "LOW"
                action = "MONITOR"
            
            table_data.append([
                product.name[:25] + '...' if len(product.name) > 25 else product.name,
                product.sku,
                str(product.current_stock),
                str(product.low_stock_threshold),
                str(shortage),
                urgency,
                action
            ])
        
        table = Table(table_data, colWidths=[4*cm, 2*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (4, 1), (4, -1), colors.lightcoral),
            ('BACKGROUND', (5, 1), (5, -1), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        elements.append(table)
    else:
        elements.append(Paragraph("🎉 NO LOW STOCK ITEMS - EXCELLENT INVENTORY MANAGEMENT!", 
                                ParagraphStyle('Success', parent=styles['Heading2'], textColor=colors.green, alignment=1)))
    
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("BizFlow Inventory System - Proactive Stock Management", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=1)))
    
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bizflow_low_stock_alert.pdf"'
    return response

def generate_supplier_report_pdf(request):
    """Generate PDF supplier report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("BizFlow Inventory Management", styles['Title']))
    elements.append(Paragraph("Supplier Performance Report", 
                            ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)))
    elements.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d at %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    suppliers = Supplier.objects.all().annotate(
        product_count=Count('product'),
        total_value=Sum(models.F('product__current_stock') * models.F('product__cost_price'))
    )
    
    table_data = [['Supplier', 'Contact', 'Products', 'Total Value', 'Phone', 'Performance']]
    
    for supplier in suppliers:
        value = supplier.total_value or 0
        if value > 100000:
            performance = "⭐️⭐️⭐️⭐️⭐️"
            bg_color = colors.lightgreen
        elif value > 50000:
            performance = "⭐️⭐️⭐️⭐️"
            bg_color = colors.lightblue
        elif value > 10000:
            performance = "⭐️⭐️⭐️"
            bg_color = colors.lightyellow
        elif supplier.product_count > 0:
            performance = "⭐️⭐️"
            bg_color = colors.lightgrey
        else:
            performance = "⭐️"
            bg_color = colors.lightgrey
        
        table_data.append([
            supplier.name[:20] + '...' if len(supplier.name) > 20 else supplier.name,
            supplier.contact_person or '-',
            str(supplier.product_count),
            f"रु{value:,.0f}" if value > 0 else "-",
            supplier.phone or '-',
            performance
        ])
    
    table = Table(table_data, colWidths=[4*cm, 3*cm, 2*cm, 3*cm, 3*cm, 2*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (5, 1), (5, -1), colors.beige),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("BizFlow - Supplier Relationship Management", 
                             ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=1)))
    
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bizflow_supplier_report.pdf"'
    return response

# Report selection view
@login_required
def generate_report(request):
    report_type = request.GET.get('type', 'stock')
    format_type = request.GET.get('format', 'pdf')  # Default to PDF
    
    if format_type == 'csv':
        if report_type == 'stock':
            return generate_stock_report_csv(request)
        elif report_type == 'low_stock':
            return generate_low_stock_report_csv(request)
        elif report_type == 'supplier':
            return generate_supplier_report_csv(request)
    else:  # PDF format
        if report_type == 'stock':
            return generate_stock_report_pdf(request)
        elif report_type == 'low_stock':
            return generate_low_stock_report_pdf(request)
        elif report_type == 'supplier':
            return generate_supplier_report_pdf(request)
    
    # Default fallback
    return generate_stock_report_pdf(request)

# Reports Dashboard View
@login_required
def reports_dashboard(request):
    # Inventory Summary
    total_products = Product.objects.filter(is_active=True).count()
    total_inventory_value = Product.objects.filter(is_active=True).aggregate(
        total_value=Sum(models.F('current_stock') * models.F('cost_price'))
    )['total_value'] or 0
    
    # Low stock items
    low_stock_items = Product.objects.filter(
        is_active=True, 
        current_stock__lte=models.F('low_stock_threshold')
    ).count()
    
    # Recent transactions (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_transactions = StockTransaction.objects.filter(
        timestamp__gte=seven_days_ago
    ).count()
    
    # Category distribution with percentage calculation
    categories = Category.objects.annotate(
        product_count=Count('product'),
        category_value=Sum(models.F('product__current_stock') * models.F('product__cost_price'))
    )
    
    # Calculate percentage for each category
    categories_with_percentage = []
    for category in categories:
        category_data = {
            'name': category.name,
            'product_count': category.product_count,
            'category_value': category.category_value or 0
        }
        
        # Calculate percentage
        if total_inventory_value > 0 and category.category_value:
            percentage = (category.category_value / total_inventory_value) * 100
            category_data['percentage'] = round(percentage, 1)
        else:
            category_data['percentage'] = 0
            
        categories_with_percentage.append(category_data)
    
    context = {
        'total_products': total_products,
        'total_inventory_value': total_inventory_value,
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions,
        'categories': categories_with_percentage,
    }
    return render(request, 'inventory/reports_dashboard.html', context)

@login_required
def admin_dashboard(request):
    # Comprehensive dashboard statistics
    stats = {
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_customers': Customer.objects.filter(is_active=True).count(),
        'total_suppliers': Supplier.objects.count(),
        'total_inventory_value': Product.objects.filter(is_active=True).aggregate(
            total_value=Sum(models.F('current_stock') * models.F('cost_price'))
        )['total_value'] or 0,
        'low_stock_items': Product.objects.filter(
            is_active=True, 
            current_stock__lte=models.F('low_stock_threshold')
        ).count(),
        'recent_orders': StockTransaction.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }
    
    # Recent activity
    recent_activity = StockTransaction.objects.select_related(
        'product', 'user'
    ).order_by('-timestamp')[:10]
    
    # Low stock alerts
    low_stock_alerts = Product.objects.filter(
        is_active=True,
        current_stock__lte=models.F('low_stock_threshold')
    )[:5]
    
    # Recent customers
    recent_customers = Customer.objects.filter(
        is_active=True
    ).order_by('-date_joined')[:5]

    context = {
        'stats': stats,
        'recent_activity': recent_activity,
        'low_stock_alerts': low_stock_alerts,
        'recent_customers': recent_customers,
    }
    return render(request, 'admin/dashboard.html', context)


    