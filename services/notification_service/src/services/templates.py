def build_booking_confirmation_html(
    booking_id: int,
    event_title: str,
    price: str,
) -> str:
    """Собирает HTML письма о бронировании."""
    return f"""
    <html>
    <body
        style="font-family: Arial, sans-serif;
               max-width: 600px; margin: 0 auto;"
    >
        <div
            style="background: #1a1a2e; color: white; padding: 20px;
                   text-align: center;"
        >
            <h1>BookingTickets</h1>
        </div>
        <div style="padding: 20px;">
            <h2>Ваше бронирование подтверждено!</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #dee2e6;">
                        <strong>Мероприятие</strong>
                    </td>
                    <td style="padding: 10px; border: 1px solid #dee2e6;">
                        {event_title}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #dee2e6;">
                        <strong>Номер бронирования</strong>
                    </td>
                    <td style="padding: 10px; border: 1px solid #dee2e6;">
                        #{booking_id}
                    </td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #dee2e6;">
                        <strong>Стоимость</strong>
                    </td>
                    <td style="padding: 10px; border: 1px solid #dee2e6;">
                        {price} ₽
                    </td>
                </tr>
            </table>
            <p style="margin-top: 20px; color: #666;">
                PDF билет прикреплён к этому письму. Покажите его на входе.
            </p>
        </div>
        <div style="background: #f8f9fa; padding: 10px; text-align: center;
                    color: #666; font-size: 12px;">
            BookingTickets — система бронирования билетов
        </div>
    </body>
    </html>
    """
