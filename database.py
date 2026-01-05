from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_address = db.Column(db.String(64), unique=True)  # Alamat wallet dummy
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
    transaction_id = db.Column(db.String(32), unique=True)  # ID unik untuk transaksi
    from_user = db.Column(db.Integer, nullable=False)
    from_address = db.Column(db.String(64))
    to_user = db.Column(db.Integer, nullable=False)
    to_address = db.Column(db.String(64))
    crypto_type = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    usd_value = db.Column(db.Float)  # Nilai transaksi dalam USD
    status = db.Column(db.String(20), default='completed')
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class BalanceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    btc_balance = db.Column(db.Float)
    eth_balance = db.Column(db.Float)
    usd_balance = db.Column(db.Float)
    total_value_usd = db.Column(db.Float)  # Total portfolio value
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)