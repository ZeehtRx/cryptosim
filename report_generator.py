from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os

def generate_transaction_report(user, wallet, transactions, crypto_prices):
    """Generate PDF report untuk transaksi user"""
    
    # Buat buffer untuk PDF
    from io import BytesIO
    buffer = BytesIO()
    
    # Setup document
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
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
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10
    )
    
    # Title
    story.append(Paragraph("Crypto Transaction Report", title_style))
    story.append(Spacer(1, 20))
    
    # User Information
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
    
    # Balance Summary
    story.append(Paragraph("Balance Summary", header_style))
    
    btc_value = wallet.btc_balance * crypto_prices['BTC']
    eth_value = wallet.eth_balance * crypto_prices['ETH']
    total_value = btc_value + eth_value + wallet.usd_balance
    
    balance_data = [
        ["Asset", "Balance", "Price (USD)", "Value (USD)", "Percentage"],
        ["Bitcoin (BTC)", f"{wallet.btc_balance:.6f}", f"${crypto_prices['BTC']:,.2f}", 
         f"${btc_value:,.2f}", f"{(btc_value/total_value*100):.1f}%" if total_value > 0 else "0%"],
        ["Ethereum (ETH)", f"{wallet.eth_balance:.6f}", f"${crypto_prices['ETH']:,.2f}", 
         f"${eth_value:,.2f}", f"{(eth_value/total_value*100):.1f}%" if total_value > 0 else "0%"],
        ["US Dollar (USD)", f"${wallet.usd_balance:,.2f}", "$1.00", 
         f"${wallet.usd_balance:,.2f}", f"{(wallet.usd_balance/total_value*100):.1f}%" if total_value > 0 else "0%"],
        ["TOTAL", "", "", f"${total_value:,.2f}", "100%"]
    ]
    
    balance_table = Table(balance_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
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
    
    # Transaction History
    story.append(Paragraph(f"Transaction History ({len(transactions)} transactions)", header_style))
    
    if transactions:
        trans_data = [["Date", "Type", "From/To", "Amount", "Value (USD)", "Status"]]
        
        for t in transactions:
            # Tentukan tipe transaksi
            if t.from_user == 0:
                trans_type = "BUY"
                from_to = "Exchange → You"
            elif t.to_user == 999:
                trans_type = "SHOPPING"
                from_to = "You → Store"
            else:
                trans_type = "TRANSFER"
                from_to = f"You → User {t.to_user}"
            
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
        story.append(Paragraph("No transactions found.", normal_style))
    
    story.append(Spacer(1, 30))
    
    # Footer
    footer_text = "This is a simulation report generated for educational purposes only. " \
                  "All data shown is fictional and for demonstration purposes."
    story.append(Paragraph(footer_text, ParagraphStyle(
        'FooterStyle',
        parent=styles['Italic'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data