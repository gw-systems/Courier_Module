from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from courier.models import Order
from datetime import datetime

@api_view(['GET'])
@permission_classes([AllowAny])
def generate_invoice_pdf(request, pk):
    """
    Generate a PDF invoice for a specific order.
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Create a file-like buffer to receive PDF data.
    buffer = BytesIO()
    
    # Create the PDF object, using the buffer as its "file."
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)

    # Container for the 'Flowable' objects
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')
    
    # --- Header ---
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 20))
    
    # Company Info (Left) & Invoice Info (Right)
    # We'll use a table for layout
    company_info = [
        [Paragraph("<b>Courier Module Inc.</b>", normal_style)],
        ["123 Logistics Way"],
        ["Tech Park, Bangalore 560100"],
        ["support@couriermodule.com"],
        ["+91 98765 43210"]
    ]
    
    invoice_info = [
        [Paragraph(f"<b>Invoice #:</b> {order.order_number}", normal_style)],
        [f"Date: {order.created_at.strftime('%Y-%m-%d')}"],
        [f"Status: {order.status.upper()}"],
        [f"Carrier: {order.carrier.name if order.carrier else 'N/A'}"],
        [f"AWB: {order.awb_number or 'N/A'}"]
    ]
    
    header_data = [[
        Table(company_info, style=[('LEFTPADDING', (0,0), (-1,-1), 0)]),
        Table(invoice_info, style=[('LEFTPADDING', (0,0), (-1,-1), 0)])
    ]]
    
    header_table = Table(header_data, colWidths=[3.5*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 30))
    
    # --- Addresses ---
    # Sender (Left) & Recipient (Right)
    sender_info = [
        [Paragraph("<b>Sender Details:</b>", bold_style)],
        [order.sender_name or "N/A"],
        [Paragraph(order.sender_address or "", normal_style)],
        [f"Pincode: {order.sender_pincode}"],
        [f"Phone: {order.sender_phone or 'N/A'}"]
    ]
    
    recipient_info = [
        [Paragraph("<b>Recipient Details:</b>", bold_style)],
        [order.recipient_name],
        [Paragraph(order.recipient_address, normal_style)],
        [f"Pincode: {order.recipient_pincode}"],
        [f"Phone: {order.recipient_phone or 'N/A'}"],
        [f"Email: {order.recipient_email or 'N/A'}"]
    ]
    
    address_data = [[
        Table(sender_info, style=[('LEFTPADDING', (0,0), (-1,-1), 0)]),
        Table(recipient_info, style=[('LEFTPADDING', (0,0), (-1,-1), 0)])
    ]]
    
    address_table = Table(address_data, colWidths=[3.5*inch, 3*inch])
    address_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,0), (1,0), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0,0), (1,0), 20),
    ]))
    elements.append(address_table)
    elements.append(Spacer(1, 30))
    
    # --- Item Details ---
    elements.append(Paragraph("<b>Shipment Details:</b>", normal_style))
    elements.append(Spacer(1, 10))
    
    item_data = [
        ["Description", "SKU", "Qty", "Weight (kg)", "Dimensions (cm)", "Amount (₹)"]
    ]
    
    # Item row
    item_desc = order.item_type or "Package"
    dims = f"{order.length}x{order.width}x{order.height}"
    item_row = [
        item_desc,
        order.sku or "-",
        str(order.quantity),
        str(order.weight),
        dims,
        f"{order.item_amount:.2f}"
    ]
    item_data.append(item_row)
    
    # Create Table
    item_table = Table(item_data, colWidths=[2*inch, 1*inch, 0.5*inch, 1*inch, 1.5*inch, 1*inch])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.Color(0.12, 0.23, 0.54)), # Brand blue
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 20))
    
    # --- Cost Breakdown ---
    # Only show if there is a cost breakdown or total cost, and status is booked/delivered etc.
    if order.total_cost:
        cost_data = [] # Headers usually not needed for simple list, but let's do customized right-aligned table
        
        # Base Freight
        freight = 0
        if order.cost_breakdown and 'freight_charge' in order.cost_breakdown:
             freight = order.cost_breakdown['freight_charge']
        
        # Surcharges (sum of others)
        surcharges = 0
        if order.cost_breakdown:
             for k, v in order.cost_breakdown.items():
                 if k != 'freight_charge' and k != 'total_charge' and isinstance(v, (int, float)):
                     surcharges += v
        
        cost_data.append(["Freight Charges:", f"₹{freight:.2f}"])
        cost_data.append(["Surcharges/Taxes:", f"₹{surcharges:.2f}"])
        cost_data.append(["Total Shipping Cost:", f"₹{order.total_cost:.2f}"])
        
        cost_table = Table(cost_data, colWidths=[5.5*inch, 1.5*inch])
        cost_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), # Total row bold
            ('LINEABOVE', (0,-1), (-1,-1), 1, colors.black),
        ]))
        elements.append(cost_table)
    
    elements.append(Spacer(1, 40))
    
    # --- Footer ---
    footer_text = "Thank you for using Courier Module Inc. This is a computer-generated invoice."
    elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=normal_style, alignment=1, fontSize=8, textColor=colors.grey)))
    
    # Build PDF
    doc.build(elements)
    
    # Init buffer position
    buffer.seek(0)
    
    filename = f"Invoice_{order.order_number}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)
