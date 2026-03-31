import io

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


def generate_ticket_pdf(
    booking_id: int,
    event_title: str,
    price: str,
    user_email: str,
) -> bytes:
    """
    Генерирует PDF билет и возвращает его как bytes.
    Использует io.BytesIO — файл в памяти, не на диске.
    """
    
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=24,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
    )

    header_style = ParagraphStyle(
        "CustomHeader",
        parent=styles["Normal"],
        fontSize=14,
        spaceAfter=10,
        textColor=colors.HexColor("#16213e"),
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=12,
        spaceAfter=8,
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    elements = []

    elements.append(Paragraph("EventHive", title_style))
    elements.append(Paragraph("Электронный билет", header_style))
    elements.append(Spacer(1, 0.5*cm))

    data = [
        ["Параметр", "Значение"],
        ["Номер бронирования", f"#{booking_id}"],
        ["Мероприятие", event_title],
        ["Стоимость", f"{price} ₽"],
        ["Email", user_email],
        ["Статус", "ПОДТВЕРЖДЕНО"],
    ]

    table = Table(data, colWidths=[6*cm, 11*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("PADDING", (0, 0), (-1, 0), 10),
        ("FONTSIZE", (0, 1), (-1, -1), 11),
        ("PADDING", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#f0f4f8"),
        ]),
        ("BACKGROUND", (1, -1), (1, -1), colors.HexColor("#d4edda")),
        ("TEXTCOLOR", (1, -1), (1, -1), colors.HexColor("#155724")),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "Покажите этот билет на входе. Спасибо за покупку!",
        normal_style,
    ))
    elements.append(Paragraph(
        "BookingTickets — система бронирования билетов",
        footer_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()