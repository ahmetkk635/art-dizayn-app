import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Sayfa Yapılandırması (Mobil Dostu)
st.set_page_config(page_title="ART DİZAYN Panel", page_icon="🏗️", layout="wide")

# Veritabanı Bağlantısı
conn = sqlite3.connect('art_dizayn.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS teklifler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, musteri TEXT, tarih TEXT, tutar REAL)''')
conn.commit()

# Basit PDF Üretici Fonksiyon
def generate_pdf(musteri, teklif_no, toplam_tutar):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "ART DİZAYN - TEKLİF FORMU")
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Müşteri: {musteri}")
    p.drawString(100, 700, f"Teklif No: {teklif_no}")
    p.drawString(100, 680, f"Toplam Tutar: {toplam_tutar:,.2f} TL")
    p.drawString(100, 640, "İşbu teklif 15 gün süreyle geçerlidir.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

st.title("🏗️ ART DİZAYN Panel")

# Mobil Sekme Yapısı
tab1, tab2, tab3 = st.tabs(["📝 Teklif & Sözleşme", "📊 Geçmiş Kayıtlar", "⚙️ Ayarlar"])

with tab1:
    st.subheader("Teklif Oluştur")
    col1, col2 = st.columns([1, 1])
    with col1:
        musteri_adi = st.text_input("Müşteri Firma/Adı", "Örnek Müşteri A.Ş.")
        teklif_no = st.text_input("Teklif No", "TEK-20260825")
    with col2:
        tarih = st.date_input("Tarih")

    st.markdown("---")
    st.write("**Ürün ve Hizmet Kalemleri**")
    
    # Varsayılan Veri
    default_data = pd.DataFrame([
        {"Ürün/Hizmet": "PVC Pencere Doğrama", "Miktar": 25.0, "Birim": "m²", "Fiyat (TL)": 2400.0},
        {"Ürün/Hizmet": "Cam Balkon Sistemleri", "Miktar": 12.0, "Birim": "m²", "Fiyat (TL)": 3200.0}
    ])
    
    # Telefonda kolayca düzenlenebilir tablo
    edited_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)
    
    # Canlı Hesaplama
    edited_df["Toplam"] = edited_df["Miktar"] * edited_df["Fiyat (TL)"]
    ara_toplam = edited_df["Toplam"].sum()
    kdv = ara_toplam * 0.20
    genel_toplam = ara_toplam + kdv

    st.metric("GENEL TOPLAM (KDV Dahil)", f"{genel_toplam:,.2f} TL")

    # PDF İndir ve Kaydet
    pdf_bytes = generate_pdf(musteri_adi, teklif_no, genel_toplam)
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Veritabanına Kaydet", use_container_width=True):
            c.execute("INSERT INTO teklifler (musteri, tarih, tutar) VALUES (?, ?, ?)",
                      (musteri_adi, str(tarih), genel_toplam))
            conn.commit()
            st.success("Veritabanına eklendi!")
    with col_btn2:
        st.download_button(
            label="📥 PDF İndir (WhatsApp ile Gönder)",
            data=pdf_bytes,
            file_name=f"{teklif_no}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

with tab2:
    st.subheader("Sistemdeki Kayıtlı Teklifler")
    kayitlar = pd.read_sql_query("SELECT * FROM teklifler ORDER BY id DESC", conn)
    st.dataframe(kayitlar, use_container_width=True)