"""Invoice PDF rendering (ReportLab platypus).

All user-entered text that ends up inside a ``Paragraph`` goes through
``_markup()``, which XML-escapes it and turns newlines into ``<br/>``.
Paragraph parses its input as mini-markup, so unescaped text such as
``<b>`` or ``&`` would either inject formatting or crash the build.
"""
import re
from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import BusinessProfile

# Single place to change how money is displayed.
CURRENCY_SYMBOL = "$"

PAGE_SIZE = letter
MARGIN = 0.75 * inch
# SimpleDocTemplate's frame pads its content by 6pt on every side; the page
# margins are reduced by that much so content lines up exactly with MARGIN.
FRAME_PADDING = 6
FOOTER_Y = 0.45 * inch

# Palette
INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
RULE = colors.HexColor("#d1d5db")
HEADER_BG = colors.HexColor("#1f2937")
ZEBRA_BG = colors.HexColor("#f3f4f6")
PAID_GREEN = colors.HexColor("#15803d")

# Control characters (other than tab/newline) are not valid in the XML-ish
# Paragraph markup and would make the parser fail.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------

def _clean(value):
    """Return value as a stripped string; None becomes ''."""
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return _CONTROL_CHARS.sub("", text).strip()


def _markup(value):
    """Escape user text for use inside a Paragraph and keep its line breaks."""
    return escape(_clean(value)).replace("\n", "<br/>")


def _money(value):
    amount = value if value is not None else Decimal("0")
    return f"{CURRENCY_SYMBOL}{Decimal(amount):,.2f}"


def _date(value):
    """Format a date/datetime as e.g. 'Nov 15, 2026'; '' when missing."""
    if not value:
        return ""
    if isinstance(value, str):  # unsaved instance assigned an ISO string
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return _clean(value)
    if hasattr(value, "hour"):  # datetime
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        value = value.date()
    return f"{value:%b} {value.day}, {value.year}"


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------

def _styles():
    base = ParagraphStyle(
        "base", fontName="Helvetica", fontSize=9.5, leading=12.5, textColor=INK
    )
    return {
        "base": base,
        "muted": ParagraphStyle("muted", parent=base, textColor=MUTED),
        "sender_name": ParagraphStyle(
            "sender_name", parent=base, fontName="Helvetica-Bold",
            fontSize=14, leading=18, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "title", parent=base, fontName="Helvetica-Bold", fontSize=26,
            leading=30, alignment=TA_RIGHT, spaceAfter=6,
        ),
        "meta_label": ParagraphStyle(
            "meta_label", parent=base, textColor=MUTED, alignment=TA_RIGHT
        ),
        "meta_value": ParagraphStyle(
            "meta_value", parent=base, fontName="Helvetica-Bold", alignment=TA_RIGHT
        ),
        "section": ParagraphStyle(
            "section", parent=base, fontName="Helvetica-Bold", fontSize=8,
            leading=10, textColor=MUTED, spaceAfter=3,
        ),
        "client_name": ParagraphStyle(
            "client_name", parent=base, fontName="Helvetica-Bold", fontSize=11, leading=14
        ),
        "th": ParagraphStyle(
            "th", parent=base, fontName="Helvetica-Bold", fontSize=8.5,
            textColor=colors.white,
        ),
        "th_right": ParagraphStyle(
            "th_right", parent=base, fontName="Helvetica-Bold", fontSize=8.5,
            textColor=colors.white, alignment=TA_RIGHT,
        ),
        "cell": base,
        "cell_right": ParagraphStyle("cell_right", parent=base, alignment=TA_RIGHT),
        "empty": ParagraphStyle(
            "empty", parent=base, textColor=MUTED, alignment=TA_CENTER
        ),
        "paid": ParagraphStyle(
            "paid", parent=base, fontName="Helvetica-Bold", fontSize=13,
            leading=16, textColor=PAID_GREEN, alignment=TA_CENTER,
        ),
        "footer_note": ParagraphStyle(
            "footer_note", parent=base, fontName="Helvetica-Oblique",
            textColor=MUTED, alignment=TA_CENTER,
        ),
    }


# --------------------------------------------------------------------------
# Page footer: "<number> · Page X of Y"
# --------------------------------------------------------------------------

def _numbered_canvas_class(footer_label):
    """Build a Canvas subclass that knows the total page count when drawing footers.

    showPage() only records each page's state; save() replays them once the
    total is known, drawing the footer onto every page before emitting it.
    """

    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total)
                super().showPage()
            super().save()

        def _draw_footer(self, total):
            width, _ = self._pagesize
            self.saveState()
            self.setStrokeColor(RULE)
            self.setLineWidth(0.5)
            self.line(MARGIN, FOOTER_Y + 12, width - MARGIN, FOOTER_Y + 12)
            self.setFont("Helvetica", 8)
            self.setFillColor(MUTED)
            parts = [footer_label] if footer_label else []
            parts.append(f"Page {self._pageNumber} of {total}")
            self.drawCentredString(width / 2, FOOTER_Y, " · ".join(parts))
            self.restoreState()

    return NumberedCanvas


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------

def _sender_name(profile, user):
    name = _clean(profile.business_name)
    if not name and user is not None:
        name = _clean(user.get_full_name()) or _clean(user.username)
    return name


def _sender_block(profile, user, styles):
    flowables = []
    name = _sender_name(profile, user)
    if name:
        flowables.append(Paragraph(_markup(name), styles["sender_name"]))
    lines = []
    if _clean(profile.address):
        lines.append(_markup(profile.address))
    for value in (profile.email, profile.phone):
        if _clean(value):
            lines.append(_markup(value))
    if _clean(profile.tax_id):
        lines.append(f"VAT / tax ID: {_markup(profile.tax_id)}")
    if lines:
        flowables.append(Paragraph("<br/>".join(lines), styles["muted"]))
    return flowables or [Spacer(1, 1)]


def _title_block(invoice, styles, width):
    rows = [
        ("Invoice no.", invoice.number or f"#{invoice.pk}"),
        ("Issue date", _date(invoice.created_at)),
        ("Due date", _date(invoice.due_date) or "—"),
        ("Status", invoice.get_status_display()),
    ]
    meta = Table(
        [
            [Paragraph(label, styles["meta_label"]),
             Paragraph(_markup(value), styles["meta_value"])]
            for label, value in rows
        ],
        colWidths=[width * 0.45, width * 0.55],
        hAlign="RIGHT",
    )
    meta.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return [Paragraph("INVOICE", styles["title"]), meta]


def _header(invoice, profile, styles, frame_width):
    left_width = frame_width * 0.55
    right_width = frame_width - left_width
    table = Table(
        [[_sender_block(profile, invoice.user, styles),
          _title_block(invoice, styles, right_width)]],
        colWidths=[left_width, right_width],
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _bill_to(invoice, styles):
    flowables = [Paragraph("BILL TO", styles["section"])]
    client = invoice.client
    name = _clean(client.name) if client else ""
    if not client or not name:
        flowables.append(Paragraph("—", styles["muted"]))
    else:
        flowables.append(Paragraph(_markup(name), styles["client_name"]))
    if client:
        details = [_markup(v) for v in (client.email, client.phone) if _clean(v)]
        if details:
            flowables.append(Paragraph("<br/>".join(details), styles["muted"]))
    return flowables


def _item_description(item):
    title = _markup(item.title)
    description = _markup(item.description)
    if title and description:
        return f'<b>{title}</b><br/><font size="8.5" color="#6b7280">{description}</font>'
    if title:
        return f"<b>{title}</b>"
    if description:
        return description
    return '<font color="#6b7280">Item</font>'


def _items_table(items, styles, frame_width):
    qty_w, unit_w, amount_w = 0.6 * inch, 1.15 * inch, 1.2 * inch
    desc_w = frame_width - qty_w - unit_w - amount_w

    data = [[
        Paragraph("Description", styles["th"]),
        Paragraph("Qty", styles["th_right"]),
        Paragraph("Unit price", styles["th_right"]),
        Paragraph("Amount", styles["th_right"]),
    ]]
    for item in items:
        line_total = item.total_amount
        if line_total is None:
            line_total = (item.amount or Decimal("0")) * (item.quantity or 0)
        data.append([
            Paragraph(_item_description(item), styles["cell"]),
            Paragraph(str(item.quantity or 0), styles["cell_right"]),
            Paragraph(_money(item.amount), styles["cell_right"]),
            Paragraph(_money(line_total), styles["cell_right"]),
        ])

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, RULE),
    ]
    if len(data) == 1:
        data.append([Paragraph("No items on this invoice.", styles["empty"]), "", "", ""])
        commands.append(("SPAN", (0, 1), (-1, 1)))
    else:
        commands.append(
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA_BG])
        )

    table = Table(
        data,
        colWidths=[desc_w, qty_w, unit_w, amount_w],
        repeatRows=1,
    )
    table.setStyle(TableStyle(commands))
    return table


def _totals(invoice, styles):
    rows = [["Subtotal", _money(invoice.total_amount)]]
    if (invoice.vat_rate or 0) > 0:
        rows.append([f"VAT ({invoice.vat_rate}%)", _money(invoice.vat_rate_amount)])
    rows.append(["Total", _money(invoice.total_amount_final)])
    last = len(rows) - 1

    table = Table(rows, colWidths=[1.6 * inch, 1.3 * inch], hAlign="RIGHT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, last - 1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), INK),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE", (0, last), (-1, last), 1, INK),
        ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
        ("FONTSIZE", (0, last), (-1, last), 12),
        ("TOPPADDING", (0, last), (-1, last), 6),
    ]))
    flowables = [table]

    if invoice.status == "paid":
        stamp = Table([[Paragraph("PAID", styles["paid"])]], colWidths=[1.3 * inch],
                      hAlign="RIGHT")
        stamp.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.5, PAID_GREEN),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        flowables += [Spacer(1, 8), stamp]
    return KeepTogether(flowables)


def _closing(profile, styles):
    flowables = []
    if _clean(profile.payment_instructions):
        flowables.append(KeepTogether([
            Paragraph("PAYMENT INSTRUCTIONS", styles["section"]),
            Paragraph(_markup(profile.payment_instructions), styles["base"]),
        ]))
    if _clean(profile.footer_note):
        flowables += [Spacer(1, 14), Paragraph(_markup(profile.footer_note), styles["footer_note"])]
    return flowables


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def build_invoice_pdf(invoice):
    """Render an invoice (active items only) to PDF and return the raw bytes."""
    # Read-only lookup: rendering (including from the public share link)
    # must not create profile rows as a side effect.
    profile = BusinessProfile.for_user_readonly(invoice.user)
    items = list(invoice.items.filter(is_active=True).order_by("id"))
    styles = _styles()
    number = _clean(invoice.number) or f"Invoice {invoice.pk}"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=MARGIN - FRAME_PADDING,
        rightMargin=MARGIN - FRAME_PADDING,
        topMargin=MARGIN - FRAME_PADDING,
        bottomMargin=MARGIN - FRAME_PADDING,
        title=number,
        author=_sender_name(profile, invoice.user),
        subject=f"Invoice {number}",
    )
    frame_width = doc.width - 2 * FRAME_PADDING

    story = [
        _header(invoice, profile, styles, frame_width),
        Spacer(1, 0.35 * inch),
        *_bill_to(invoice, styles),
        Spacer(1, 0.3 * inch),
        _items_table(items, styles, frame_width),
        Spacer(1, 0.2 * inch),
        _totals(invoice, styles),
    ]
    closing = _closing(profile, styles)
    if closing:
        story += [Spacer(1, 0.35 * inch), *closing]

    doc.build(story, canvasmaker=_numbered_canvas_class(number))
    return buffer.getvalue()
