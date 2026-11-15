from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def build_invoice_pdf(invoice):
    """Render an invoice (active items only) to PDF and return the raw bytes."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"INVOICE #{invoice.id}")

    # Invoice details
    p.setFont("Helvetica", 12)
    y_position = height - 100

    if invoice.client:
        p.drawString(50, y_position, f"Client: {invoice.client.name}")
        y_position -= 20
        if invoice.client.email:
            p.drawString(50, y_position, f"Email: {invoice.client.email}")
            y_position -= 20
        if invoice.client.phone:
            p.drawString(50, y_position, f"Phone: {invoice.client.phone}")
            y_position -= 20

    p.drawString(50, y_position, f"Created: {invoice.created_at.strftime('%Y-%m-%d')}")
    y_position -= 20
    if invoice.due_date:
        p.drawString(50, y_position, f"Due Date: {invoice.due_date}")
        y_position -= 20

    # Items table header
    y_position -= 30
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y_position, "Description")
    p.drawString(300, y_position, "Qty")
    p.drawString(350, y_position, "Amount")
    p.drawString(450, y_position, "Total")
    y_position -= 20

    # Items
    p.setFont("Helvetica", 10)
    for item in invoice.items.filter(is_active=True):
        p.drawString(50, y_position, str(item.description or item.title)[:40])
        p.drawString(300, y_position, str(item.quantity))
        p.drawString(350, y_position, f"${item.amount}")
        p.drawString(450, y_position, f"${item.total_amount}")
        y_position -= 15

    # Totals
    y_position -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, y_position, f"Subtotal: ${invoice.total_amount}")
    y_position -= 20
    if invoice.vat_rate > 0:
        p.drawString(350, y_position, f"VAT ({invoice.vat_rate}%): ${invoice.vat_rate_amount}")
        y_position -= 20
    p.drawString(350, y_position, f"Total: ${invoice.total_amount_final}")

    p.showPage()
    p.save()

    return buffer.getvalue()
