from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import random
import string
import os
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PIL import Image as PILImage

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kunci-rahasia-tugas-kuliah'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simulation.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/qr_codes'
app.config['REPORT_FOLDER'] = 'reports'

# Buat folder OS
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)
os.makedirs('email_simulations', exist_ok=True)

db = SQLAlchemy(app)

#  MODELS 
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_address = db.Column(db.String(64), unique=True)
    btc_balance = db.Column(db.Float, default=0.0)
    eth_balance = db.Column(db.Float, default=0.0)
    usd_balance = db.Column(db.Float, default=1000.0)
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price_usd = db.Column(db.Float, nullable=False)
    price_btc = db.Column(db.Float)
    price_eth = db.Column(db.Float)
    image_url = db.Column(db.String(200))
    
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(32), unique=True)
    from_user = db.Column(db.Integer, nullable=False)
    from_address = db.Column(db.String(64))
    to_user = db.Column(db.Integer, nullable=False)
    to_address = db.Column(db.String(64))
    crypto_type = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float)
    status = db.Column(db.String(20), default='completed')
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class BalanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    btc_balance = db.Column(db.Float)
    eth_balance = db.Column(db.Float)
    usd_balance = db.Column(db.Float)
    total_value_usd = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

#  KONFIGURASI NILAI
CRYPTO_PRICES = {
    'BTC': 50000.0,
    'ETH': 3000.0
}

#  FUNGSI HELPER 
def generate_wallet_address():
    characters = string.ascii_letters + string.digits
    return '0x' + ''.join(random.choice(characters) for _ in range(40))

def generate_transaction_id():
    return ''.join(random.choice('0123456789ABCDEF') for _ in range(16))

def save_balance_history(user_id):
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if wallet:
        total_value = (wallet.btc_balance * CRYPTO_PRICES['BTC'] + 
                      wallet.eth_balance * CRYPTO_PRICES['ETH'] + 
                      wallet.usd_balance)
        
        history = BalanceHistory(
            user_id=user_id,
            btc_balance=wallet.btc_balance,
            eth_balance=wallet.eth_balance,
            usd_balance=wallet.usd_balance,
            total_value_usd=total_value
        )
        db.session.add(history)
        db.session.commit()

def generate_wallet_qr(wallet_address, user_id):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr_data = f"crypto:{wallet_address}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        qr_filename = f"static/qr_codes/wallet_{user_id}.png"
        img.save(qr_filename)
        
        return qr_filename
    except Exception as e:
        print(f"Error generating QR: {e}")
        return None

def send_simulation_email(to_email, subject, transaction_id, crypto_type, amount, usd_value, product_name=None):
    if not to_email or "@" not in to_email:
        to_email = "simulation@localhost"
    
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
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = 'noreply@cryptosimulator.edu'
    msg['To'] = to_email
    msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    html_part = MIMEText(email_content, 'html')
    msg.attach(html_part)
    
    try:
        os.makedirs('email_simulations', exist_ok=True)
        filename = f"email_simulations/{transaction_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.eml"
        
        with open(filename, 'w') as f:
            f.write(msg.as_string())
        
        print(f"[EMAIL SIMULATION] Email saved to: {filename}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def generate_transaction_report(user, wallet, transactions, crypto_prices):
    from io import BytesIO
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=10
    )
    
    story.append(Paragraph("Crypto Transaction Report", title_style))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("User Information", header_style))
    
    user_data = [
        ["Username:", user.username],
        ["Email:", user.email or "Not provided"],
        ["User ID:", str(user.id)],
        ["Wallet Address:", wallet.wallet_address],
        ["Report Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ]
    
    user_table = Table(user_data, colWidths=[2*inch, 4*inch])
    user_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    story.append(user_table)
    story.append(Spacer(1, 20))
    
    btc_value = wallet.btc_balance * crypto_prices['BTC']
    eth_value = wallet.eth_balance * crypto_prices['ETH']
    total_value = btc_value + eth_value + wallet.usd_balance
    
    balance_data = [
        ["Asset", "Balance", "Price (USD)", "Value (USD)"],
        ["Bitcoin (BTC)", f"{wallet.btc_balance:.6f}", f"${crypto_prices['BTC']:,.2f}", f"${btc_value:,.2f}"],
        ["Ethereum (ETH)", f"{wallet.eth_balance:.6f}", f"${crypto_prices['ETH']:,.2f}", f"${eth_value:,.2f}"],
        ["US Dollar (USD)", f"${wallet.usd_balance:,.2f}", "$1.00", f"${wallet.usd_balance:,.2f}"],
        ["TOTAL", "", "", f"${total_value:,.2f}"]
    ]
    
    balance_table = Table(balance_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    balance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498DB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2ECC71')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(balance_table)
    story.append(Spacer(1, 20))
    
    if transactions:
        trans_data = [["Date", "Type", "From/To", "Amount", "Value (USD)", "Status"]]
        
        for t in transactions:
            if t.from_user == 0:
                trans_type = "BUY"
                from_to = "Exchange → You"
            elif t.to_user == 999:
                trans_type = "SHOPPING"
                from_to = "You → Store"
            else:
                trans_type = "SELL" if t.to_user == 0 else "TRANSFER"
                from_to = f"You → {'Exchange' if t.to_user == 0 else f'User {t.to_user}'}"
            
            trans_data.append([
                t.timestamp.strftime("%Y-%m-%d\n%H:%M"),
                trans_type,
                from_to,
                f"{t.amount:.6f} {t.crypto_type}",
                f"${t.usd_value:,.2f}" if t.usd_value else "-",
                t.status
            ])
        
        trans_table = Table(trans_data, colWidths=[1*inch, 0.8*inch, 1.5*inch, 1.2*inch, 1*inch, 0.8*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9F9')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F3F4')])
        ]))
        story.append(trans_table)
    else:
        story.append(Paragraph("No transactions found.", ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10
        )))
    
    story.append(Spacer(1, 30))
    
    footer_text = "This is a simulation report generated for educational purposes only. " \
                  "All data shown is fictional and for demonstration purposes."
    story.append(Paragraph(footer_text, ParagraphStyle(
        'FooterStyle',
        parent=styles['Italic'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )))
    
    doc.build(story)
    
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

# ROUTES 
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, password=password, email=email)
            db.session.add(user)
            db.session.commit()
            
            wallet_address = generate_wallet_address()
            wallet = Wallet(
                user_id=user.id, 
                usd_balance=1000.0,
                wallet_address=wallet_address
            )
            db.session.add(wallet)
            db.session.commit()
            
            generate_wallet_qr(wallet_address, user.id)
            save_balance_history(user.id)
        
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    # Hitung portfolio
    btc_value = wallet.btc_balance * CRYPTO_PRICES['BTC']
    eth_value = wallet.eth_balance * CRYPTO_PRICES['ETH']
    total_value = btc_value + eth_value + wallet.usd_balance
    
    portfolio = {
        'BTC': btc_value,
        'ETH': eth_value,
        'USD': wallet.usd_balance
    }
    
    if total_value > 0:
        portfolio_percent = {
            'BTC': (btc_value/total_value)*100,
            'ETH': (eth_value/total_value)*100,
            'USD': (wallet.usd_balance/total_value)*100
        }
    else:
        portfolio_percent = {'BTC': 0, 'ETH': 0, 'USD': 0}
    
    # Ambil data untuk chart
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    history = BalanceHistory.query.filter(
        BalanceHistory.user_id == user_id,
        BalanceHistory.timestamp >= seven_days_ago
    ).order_by(BalanceHistory.timestamp).all()
    
    chart_data = {
        'dates': [h.timestamp.strftime('%Y-%m-%d %H:%M') for h in history],
        'total_values': [h.total_value_usd for h in history],
        'btc_values': [h.btc_balance * CRYPTO_PRICES['BTC'] for h in history],
        'eth_values': [h.eth_balance * CRYPTO_PRICES['ETH'] for h in history],
        'usd_values': [h.usd_balance for h in history]
    }
    
    # Ambil transaksi terbaru
    transactions = Transaction.query.filter(
        (Transaction.from_user == user_id) | (Transaction.to_user == user_id)
    ).order_by(Transaction.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         user=user,
                         wallet=wallet,
                         prices=CRYPTO_PRICES,
                         chart_data=chart_data,
                         portfolio=portfolio,
                         portfolio_percent=portfolio_percent,
                         transactions=transactions)

@app.route('/exchange')
def exchange():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    return render_template('exchange.html', 
                         user=user,
                         wallet=wallet, 
                         prices=CRYPTO_PRICES)

@app.route('/api/buy_crypto', methods=['POST'])
def buy_crypto():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    crypto_type = data.get('crypto_type')
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    price_per_unit = CRYPTO_PRICES[crypto_type]
    total_usd = amount * price_per_unit
    
    if wallet.usd_balance < total_usd:
        return jsonify({'error': 'Insufficient USD balance'}), 400
    
    wallet.usd_balance -= total_usd
    if crypto_type == 'BTC':
        wallet.btc_balance += amount
    else:
        wallet.eth_balance += amount
    
    transaction_id = generate_transaction_id()
    transaction = Transaction(
        transaction_id=transaction_id,
        from_user=0,
        from_address='EXCHANGE',
        to_user=user_id,
        to_address=wallet.wallet_address,
        crypto_type=crypto_type,
        amount=amount,
        usd_value=total_usd,
        description=f'Buy {amount} {crypto_type} from Exchange'
    )
    
    db.session.add(transaction)
    save_balance_history(user_id)
    db.session.commit()
    
    send_simulation_email(
        to_email=user.email,
        subject="Crypto Purchase Confirmation",
        transaction_id=transaction_id,
        crypto_type=crypto_type,
        amount=amount,
        usd_value=total_usd
    )
    
    return jsonify({
        'success': True,
        'transaction_id': transaction_id,
        'new_balance': {
            'usd': wallet.usd_balance,
            'btc': wallet.btc_balance,
            'eth': wallet.eth_balance
        }
    })

@app.route('/api/sell_crypto', methods=['POST'])
def sell_crypto():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    crypto_type = data.get('crypto_type')
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    # CEK SALDO CRYPTO YANG CUKUP
    if crypto_type == 'BTC':
        if wallet.btc_balance < amount:
            return jsonify({'error': f'Insufficient BTC balance. You have {wallet.btc_balance} BTC, trying to sell {amount} BTC'}), 400
    else:  # ETH
        if wallet.eth_balance < amount:
            return jsonify({'error': f'Insufficient ETH balance. You have {wallet.eth_balance} ETH, trying to sell {amount} ETH'}), 400
    
    # Hitung nilai dalam USD
    price_per_unit = CRYPTO_PRICES[crypto_type]
    total_usd = amount * price_per_unit
    
    # Update saldo
    if crypto_type == 'BTC':
        wallet.btc_balance -= amount
    else:
        wallet.eth_balance -= amount
    
    wallet.usd_balance += total_usd
    
    # Catat transaksi
    transaction_id = generate_transaction_id()
    transaction = Transaction(
        transaction_id=transaction_id,
        from_user=user_id,
        from_address=wallet.wallet_address,
        to_user=0,  # 0 = exchange
        to_address='EXCHANGE',
        crypto_type=crypto_type,
        amount=amount,
        usd_value=total_usd,
        description=f'Sell {amount} {crypto_type} to Exchange'
    )
    
    db.session.add(transaction)
    save_balance_history(user_id)
    db.session.commit()
    
    # Kirim notifikasi email
    send_simulation_email(
        to_email=user.email,
        subject="Crypto Sale Confirmation",
        transaction_id=transaction_id,
        crypto_type=crypto_type,
        amount=amount,
        usd_value=total_usd
    )
    
    return jsonify({
        'success': True,
        'transaction_id': transaction_id,
        'new_balance': {
            'usd': wallet.usd_balance,
            'btc': wallet.btc_balance,
            'eth': wallet.eth_balance
        }
    })

@app.route('/wallet')
def wallet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    transactions = Transaction.query.filter(
        (Transaction.from_user == user_id) | (Transaction.to_user == user_id)
    ).order_by(Transaction.timestamp.desc()).limit(20).all()
    
    qr_path = f"/static/qr_codes/wallet_{user_id}.png"
    
    return render_template('wallet.html', 
                         user=user,
                         wallet=wallet, 
                         transactions=transactions,
                         prices=CRYPTO_PRICES,
                         qr_path=qr_path)

@app.route('/wallet/qr')
def wallet_qr():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    return render_template('qr_wallet.html',
                         user=user,
                         wallet=wallet,
                         qr_path=f"/static/qr_codes/wallet_{user_id}.png")
    

product_image_mapping = {
    "Gaming Laptop Pro": "laptop.jpg",
    "iPhone 15 Pro": "iphone.jpg",
    "Wireless Headphones": "headphones.jpg",
    "Gaming Mouse RGB": "mouse.jpg",
    "Mechanical Keyboard": "keyboard.jpg",
    "4K Monitor": "monitor.jpg",
    "Smart Watch": "watch.jpg",
    "Portable Speaker": "speaker.jpg",
    "Tablet Pro": "tablet.jpg",
    "DSLR Camera": "camera.jpg"
}

@app.route('/ecommerce')
def ecommerce():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    products = Product.query.all()
    
    for product in products:
        if not product.price_btc:
            product.price_btc = product.price_usd / CRYPTO_PRICES['BTC']
            product.price_eth = product.price_usd / CRYPTO_PRICES['ETH']
    db.session.commit()
    
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    return render_template('ecommerce.html', 
                         user=user,
                         products=products, 
                         wallet=wallet,
                         prices=CRYPTO_PRICES)
    
    return render_template('ecommerce.html', products=products, user=current_user, wallet=current_wallet)
@app.route('/api/pay_with_crypto', methods=['POST'])
def pay_with_crypto():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    product_id = data.get('product_id')
    crypto_type = data.get('crypto_type')
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    if crypto_type == 'BTC':
        amount_needed = product.price_btc
        current_balance = wallet.btc_balance
    else:
        amount_needed = product.price_eth
        current_balance = wallet.eth_balance
    
    if current_balance < amount_needed:
        return jsonify({'error': f'Insufficient {crypto_type} balance'}), 400
    
    if crypto_type == 'BTC':
        wallet.btc_balance -= amount_needed
    else:
        wallet.eth_balance -= amount_needed
    
    transaction_id = generate_transaction_id()
    transaction = Transaction(
        transaction_id=transaction_id,
        from_user=user_id,
        from_address=wallet.wallet_address,
        to_user=999,
        to_address='ECOMMERCE_STORE',
        crypto_type=crypto_type,
        amount=amount_needed,
        usd_value=amount_needed * CRYPTO_PRICES[crypto_type],
        description=f'Purchase: {product.name}',
        status='completed'
    )
    
    db.session.add(transaction)
    save_balance_history(user_id)
    db.session.commit()
    
    send_simulation_email(
        to_email=user.email,
        subject="E-commerce Purchase Confirmation",
        transaction_id=transaction_id,
        crypto_type=crypto_type,
        amount=amount_needed,
        usd_value=amount_needed * CRYPTO_PRICES[crypto_type],
        product_name=product.name
    )
    
    return jsonify({
        'success': True,
        'transaction_id': transaction_id,
        'message': f'Purchased {product.name} successfully!',
        'new_balance': {
            'btc': wallet.btc_balance,
            'eth': wallet.eth_balance
        }
    })

@app.route('/api/get_balance_history')
def get_balance_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    history = BalanceHistory.query.filter_by(user_id=user_id)\
        .order_by(BalanceHistory.timestamp.desc())\
        .limit(50).all()
    
    data = [{
        'timestamp': h.timestamp.strftime('%Y-%m-%d %H:%M'),
        'total_value': h.total_value_usd,
        'btc_value': h.btc_balance * CRYPTO_PRICES['BTC'],
        'eth_value': h.eth_balance * CRYPTO_PRICES['ETH'],
        'usd_value': h.usd_balance
    } for h in history]
    
    return jsonify(data)

@app.route('/generate_report')
def generate_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    
    start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    transactions = Transaction.query.filter(
        ((Transaction.from_user == user_id) | (Transaction.to_user == user_id)) &
        (Transaction.timestamp >= start_date)
    ).order_by(Transaction.timestamp.desc()).all()
    
    pdf_data = generate_transaction_report(user, wallet, transactions, CRYPTO_PRICES)
    
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=transaction_report_{user_id}_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

@app.route('/api/send_test_email')
def send_test_email():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if not user.email:
        return jsonify({'error': 'No email registered'}), 400
    
    success = send_simulation_email(
        to_email=user.email,
        subject="Test Notification - Crypto Simulator",
        transaction_id="TEST123",
        crypto_type="BTC",
        amount=0.01,
        usd_value=500,
        product_name="Test Product"
    )
    
    if success:
        return jsonify({'success': True, 'message': 'Test email sent!'})
    else:
        return jsonify({'error': 'Failed to send email'}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/api/get_user_info')
def get_user_info():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if user:
        return jsonify({
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.strftime('%Y-%m-%d')
        })
    else:
        return jsonify({'error': 'User not found'}), 404
    

#  SEED DATABASE 
def seed_database():
    with app.app_context():
        db.create_all()
        
        if Product.query.count() == 0:
            products = [
                Product(
                    name="Laptop Gaming ASUS ROG",
                    description="Laptop gaming dengan RTX 4060, RAM 16GB",
                    price_usd=1200,
                    price_btc=1200 / CRYPTO_PRICES['BTC'],
                    price_eth=1200 / CRYPTO_PRICES['ETH'],
                    image_url="https://images.unsplash.com/photo-1541140532154-b024d705b90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                ),
                Product(
                    name="iPhone 15 Pro",
                    description="Smartphone flagship Apple",
                    price_usd=999,
                    price_btc=999 / CRYPTO_PRICES['BTC'],
                    price_eth=999 / CRYPTO_PRICES['ETH'],
                    image_url="https://images.unsplash.com/photo-1695048133142-1a20484d2569?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                ),
                Product(
                    name="Sony WH-1000XM5",
                    description="Headphone noise cancelling terbaik",
                    price_usd=299,
                    price_btc=299 / CRYPTO_PRICES['BTC'],
                    price_eth=299 / CRYPTO_PRICES['ETH'],
                    image_url="https://images.unsplash.com/photo-1541140532154-b024d705b90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                ),
                Product(
                    name="Logitech MX Master 3S",
                    description="Mouse wireless premium",
                    price_usd=99,
                    price_btc=99 / CRYPTO_PRICES['BTC'],
                    price_eth=99 / CRYPTO_PRICES['ETH'],
                    image_url="https://images.unsplash.com/photo-1527814050087-3793815479db?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                ),
                Product(
                    name="Keychron K8 Pro",
                    description="Keyboard mechanical wireless",
                    price_usd=119,
                    price_btc=119 / CRYPTO_PRICES['BTC'],
                    price_eth=119 / CRYPTO_PRICES['ETH'],
                    image_url="https://images.unsplash.com/photo-1541140532154-b024d705b90a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80"
                )
            ]
            for product in products:
                db.session.add(product)
            db.session.commit()
            print("Database seeded with sample products!")


#  MAIN 
if __name__ == '__main__':
    seed_database()
    app.run(debug=True, port=5000)
