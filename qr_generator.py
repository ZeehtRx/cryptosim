import qrcode
import os
from PIL import Image
import io
import base64

def generate_wallet_qr(wallet_address, user_id):
    """Generate QR code untuk wallet address"""
    try:
        # Buat QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Data untuk QR code
        qr_data = f"crypto:{wallet_address}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Buat image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Tambahkan logo di tengah 
        try:
            logo = Image.open('static/images/logo.png')
            img = add_logo_to_qr(img, logo)
        except:
            pass
        
        # Simpan file
        qr_filename = f"static/qr_codes/wallet_{user_id}.png"
        img.save(qr_filename)
        
        return qr_filename
    except Exception as e:
        print(f"Error generating QR: {e}")
        return None

def add_logo_to_qr(qr_img, logo_img):
    """Tambahkan logo di tengah QR code"""
    # Resize logo
    logo_size = qr_img.size[0] // 5
    logo_img = logo_img.resize((logo_size, logo_size))
    
    # Paste logo di tengah
    pos = ((qr_img.size[0] - logo_img.size[0]) // 2,
           (qr_img.size[1] - logo_img.size[1]) // 2)
    
    qr_img.paste(logo_img, pos)
    return qr_img

def generate_qr_base64(wallet_address):
    """Generate QR code dan return sebagai base64 string (untuk embed di HTML)"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(wallet_address)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert ke base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"