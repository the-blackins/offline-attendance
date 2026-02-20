"""
QR code generation utility.
"""
import io
import base64
import qrcode


def generate_qr_base64(data, box_size=10, border=2):
    """
    Generate a QR code from data and return it as a base64-encoded PNG string.
    This can be embedded directly in HTML: <img src="data:image/png;base64,..." />
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"
