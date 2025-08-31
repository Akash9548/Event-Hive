import qrcode
import os
from PIL import Image

def generate_qr(data, booking_id):
    """Generate a QR code image and save it temporarily."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Create temp directory if it doesn't exist
    temp_dir = "temp_qr"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # Save QR code
    qr_path = f"{temp_dir}/qr_{booking_id}.png"
    img.save(qr_path)
    
    return qr_path