import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

# Untuk simulasi, kita akan simpan email di file (bukan kirim real)
# Tapi tetap sediakan opsi untuk kirim real jika mau

def send_simulation_email(to_email, subject, transaction_id, crypto_type, amount, usd_value, product_name=None):
    """
    Simulasi pengiriman email.
    Untuk tugas kuliah, kita simpan sebagai file .eml
    """
    
    # Jika email tidak ada, simpan ke folder local
    if not to_email or "@" not in to_email:
        to_email = "simulation@localhost"
    
    # Buat konten email
    email_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2C3E50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background-color: #f9f9f9; }}
            .transaction-details {{ background-color: white; padding: 20px; border-radius: 5px; border: 1px solid #ddd; }}
            .footer {{ text-align: center; padding: 20px; color: #777; font-size: 12px; }}
            .success {{ color: #27ae60; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Crypto Simulator Notification</h1>
            </div>
            
            <div class="content">
                <h2>{subject}</h2>
                
                <div class="transaction-details">
                    <p><strong>Transaction ID:</strong> {transaction_id}</p>
                    <p><strong>Date & Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Status:</strong> <span class="success">COMPLETED</span></p>
                    
                    <hr>
                    
                    <h3>Transaction Details:</h3>
                    <p><strong>Crypto Type:</strong> {crypto_type}</p>
                    <p><strong>Amount:</strong> {amount:.6f} {crypto_type}</p>
                    <p><strong>Value (USD):</strong> ${usd_value:,.2f}</p>
    """
    
    if product_name:
        email_content += f"""
                    <p><strong>Product:</strong> {product_name}</p>
        """
    
    email_content += f"""
                </div>
                
                <p style="margin-top: 20px;">
                    This is a simulation email for educational purposes.<br>
                    No real transaction has occurred.
                </p>
            </div>
            
            <div class="footer">
                <p>Crypto Simulator - Educational Project</p>
                <p>This email was generated automatically. Please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Buat MIME message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = 'noreply@cryptosimulator.edu'
    msg['To'] = to_email
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    # Attach HTML version
    html_part = MIMEText(email_content, 'html')
    msg.attach(html_part)
    
    # Simpan ke file (untuk simulasi)
    try:
        os.makedirs('email_simulations', exist_ok=True)
        filename = f"email_simulations/{transaction_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.eml"
        
        with open(filename, 'w') as f:
            f.write(msg.as_string())
        
        print(f"[EMAIL SIMULATION] Email saved to: {filename}")
        
        
        # send_real_email(msg)
        
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def send_real_email(msg):
    """Fungsi untuk mengirim email real """
    try:
        # Konfigurasi SMTP 
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = "your_email@gmail.com"
        smtp_password = "your_app_password"
        
        # Koneksi ke server SMTP
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        
        # Kirim email
        server.send_message(msg)
        server.quit()
        
        print("[EMAIL SENT] Real email sent successfully")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send real email: {e}")
        return False