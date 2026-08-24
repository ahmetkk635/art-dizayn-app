import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
import base64
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="ART DİZAYN ERP Panel", page_icon="🏗️", layout="wide")

# PDF / Baskı Özel CSS Stili (Sayfadaki butonları gizler, teklifi tam sayfa yapar)
st.markdown("""
<style>
@media print {
    [data-testid="stSidebar"], .stButton, header, footer, .stDownloadButton, [data-testid="stHeader"] {
        display: none !important;
    }
    .main .block-container {
        padding: 0 !important;
        margin: 0 !important;
    }
}
</style>
""", unsafe_allow_html=True)

# Veritabanı Mimarisi
conn = sqlite3.connect('art_dizayn_full.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS musteriler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_adi TEXT, yetkili TEXT, telefon TEXT, adres TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS isler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, musteri_id INTEGER, isin_cinsi TEXT, toplam_tutar REAL, tarih TEXT, montaj_tarihi TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tahsilatlar 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, is_id INTEGER, musteri_id INTEGER, odenen_tutar REAL, tarih TEXT, aciklama TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS stok 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, malzeme_adi TEXT, kategori TEXT, miktar REAL, birim TEXT, kritik_seviye REAL)''')
conn.commit()

if 'teklif_kalemleri' not in st.session_state:
    st.session_state.teklif_kalemleri = []

def to_excel():
    output = BytesIO()
    with pd.ExcelWriter(output) as writer:
        df_m = pd.read_sql_query("SELECT id as 'Müşteri No', firma_adi as 'Firma', yetkili as 'Yetkili', telefon as 'Telefon', adres as 'Adres' FROM musteriler", conn)
        df_m.to_excel(writer, sheet_name='Müşteriler', index=False)
        
        df_i = pd.read_sql_query("SELECT id as 'İş No', musteri_id as 'Müşteri No', isin_cinsi as 'İşin Cinsi', toplam_tutar as 'Tutar (TL)', tarih as 'Sözleşme Tarihi', montaj_tarihi as 'Montaj Tarihi' FROM isler", conn)
        df_i.to_excel(writer, sheet_name='İşler ve Montajlar', index=False)
        
        df_t = pd.read_sql_query("SELECT id as 'Tahsilat No', is_id as 'İş No', musteri_id as 'Müşteri No', odenen_tutar as 'Ödenen (TL)', tarih as 'Tarih', aciklama as 'Açıklama' FROM tahsilatlar", conn)
        df_t.to_excel(writer, sheet_name='Tahsilat Hareketleri', index=False)
        
        df_s = pd.read_sql_query("SELECT id as 'Stok No', malzeme_adi as 'Malzeme', kategori as 'Kategori', miktar as 'Miktar', birim as 'Birim', kritik_seviye as 'Kritik Seviye' FROM stok", conn)
        df_s.to_excel(writer, sheet_name='Depo Stok', index=False)
        
    processed_data = output.getvalue()
    return processed_data

st.title("🏗️ ART DİZAYN - Bütünleşik İmalat & Finans ERP Paneli")

col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.caption("ART DİZAYN PVC, Alüminyum & Cam Balkon Sistemleri Yönetim Ekranı")
with col_head2:
    excel_data = to_excel()
    st.download_button(
        label="📊 Tüm Verileri Excel Olarak İndir",
        data=excel_data,
        file_name=f"ART_DIZAYN_Sistem_Raporu_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

st.markdown("---")

tab_grafik, tab_teklif, tab_musteri, tab_hesap, tab_proforma, tab_takvim, tab_stok = st.tabs([
    "📊 Finans & Grafikler", 
    "📄 Teklif Formu Oluştur",
    "👤 Müşteri & Borç Arama", 
    "📏 Ölçü & Metraj Hesabı",
    "📑 Proforma & WhatsApp", 
    "🗓️ Şantiye Montaj Takvimi",
    "📦 Depo & Stok Takibi"
])

# ---------------------------------------------------------
# 1. FİNANS VE GRAFİKLER
# ---------------------------------------------------------
with tab_grafik:
    st.subheader("📈 Genel Finansal Özet")
    df_isler = pd.read_sql_query("SELECT * FROM isler", conn)
    df_tahsilat = pd.read_sql_query("SELECT * FROM tahsilatlar", conn)
    
    toplam_is = df_isler['toplam_tutar'].sum() if not df_isler.empty else 0.0
    toplam_tahsilat = df_tahsilat['odenen_tutar'].sum() if not df_tahsilat.empty else 0.0
    kalan_alacak = toplam_is - toplam_tahsilat
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam İş Hacmi", f"{toplam_is:,.2f} TL")
    col2.metric("Tahsil Edilen (Kasa)", f"{toplam_tahsilat:,.2f} TL")
    col3.metric("Kalan Net Alacak", f"{kalan_alacak:,.2f} TL")

# ---------------------------------------------------------
# 2. TEKLİF FORMU OLUŞTURUCU (KUSURSUZ HTML + PRINT CSS)
# ---------------------------------------------------------
with tab_teklif:
    st.subheader("📄 Kurumsal Teklif Formu Hazırlama Paneli")
    
    col_tf1, col_tf2 = st.columns([1, 1])
    
    with col_tf1:
        st.write("**1. Logo & Müşteri Bilgileri**")
        uploaded_logo = st.file_uploader("Firma Logosu Yükle (PNG / JPG)", type=["png", "jpg", "jpeg"])
        
        logo_base64 = ""
        if uploaded_logo is not None:
            bytes_data = uploaded_logo.getvalue()
            logo_base64 = f"data:image/png;base64,{base64.b64encode(bytes_data).decode()}"
            
        tf_musteri = st.text_input("Müşteri / Firma Adı", "Örnek İnşaat Ltd. Şti.")
        tf_yetkili = st.text_input("Yetkili Kişi", "Ahmet Yılmaz")
        tf_tel = st.text_input("Müşteri Telefon", "+90 532 000 00 00")
        tf_no = st.text_input("Teklif No", f"ART-{datetime.now().strftime('%Y%m%d')}-01")
        tf_tarih = st.date_input("Teklif Tarihi")
        
        st.markdown("---")
        st.write("**2. Ürün / Kalem Ekleme**")
        kalem_aciklama = st.text_input("Ürün / Hizmet Detayı", "8mm Füme Camlı Isıcamlı Balkon Kapatma Sistemi")
        c_k1, c_k2, c_k3 = st.columns(3)
        kalem_miktar = c_k1.number_input("Miktar / Ölçü", value=15.0, step=1.0)
        kalem_birim = c_k2.selectbox("Birim", ["m²", "Metre", "Adet", "Set", "Takım"])
        kalem_fiyat = c_k3.number_input("Birim Fiyat (TL)", value=3500.0, step=100.0)
        
        if st.button("➕ Kalemi Teklife Ekle", use_container_width=True):
            toplam = kalem_miktar * kalem_fiyat
            st.session_state.teklif_kalemleri.append({
                "Sıra": len(st.session_state.teklif_kalemleri) + 1,
                "Açıklama": kalem_aciklama,
                "Miktar": kalem_miktar,
                "Birim": kalem_birim,
                "Birim Fiyat": kalem_fiyat,
                "Toplam Tutar": toplam
            })
            st.rerun()
            
        if st.button("🗑️ Kalemleri Temizle"):
            st.session_state.teklif_kalemleri = []
            st.rerun()

        st.markdown("---")
        st.write("**3. Özel Teklif Şartları & Notlar**")
        tf_sartlar = st.text_area("Teklif Şartları Metni", 
"""1. Bu teklif verildiği tarihten itibaren 15 gün süreyle geçerlidir.
2. Ödeme koşulları: %50 Siparişte, %50 Montaj tesliminde tahsil edilir.
3. Teslimat süresi ölçü alımından itibaren 10 iş günüdür.
4. Ürünlerimiz 2 yıl sızdırmazlık ve mekanizma garantisi altındadır.""", height=130)

    with col_tf2:
        st.write("**4. Resmi Teklif Formu Önizlemesi**")
        
        logo_html = f'<img src="{logo_base64}" style="max-height: 55px; margin-bottom: 5px;">' if logo_base64 else '<h1 style="color:#0F2C59; margin:0; font-family:sans-serif; font-weight:bold;">ART DİZAYN</h1>'
        
        # HTML Tablo Satırlarını Oluşturma
        table_rows_html = ""
        ara_toplam = 0.0
        
        for item in st.session_state.teklif_kalemleri:
            ara_toplam += item["Toplam Tutar"]
            table_rows_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 12px;">
                <td style="padding: 8px; text-align: center;">{item['Sıra']}</td>
                <td style="padding: 8px;">{item['Açıklama']}</td>
                <td style="padding: 8px; text-align: center;">{item['Miktar']} {item['Birim']}</td>
                <td style="padding: 8px; text-align: right;">{item['Birim Fiyat']:,.2f} TL</td>
                <td style="padding: 8px; text-align: right; font-weight: bold;">{item['Toplam Tutar']:,.2f} TL</td>
            </tr>
            """
            
        kdv_tutar = ara_toplam * 0.20
        genel_toplam = ara_toplam + kdv_tutar
        formatted_sartlar = tf_sartlar.replace("\n", "<br>")
        
        # TEK PARÇA TEKLİF KARTI (HTML/CSS)
        teklif_html_full = f"""
        <div id="teklif-formu-print" style="border: 1px solid #d1d5db; padding: 25px; border-radius: 8px; background-color: #ffffff; font-family: 'Helvetica Neue', Arial, sans-serif; color: #1f2937;">
            
            <!-- HEADER -->
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 3px solid #0F2C59; padding-bottom: 12px; margin-bottom: 15px;">
                <div>
                    {logo_html}
                    <p style="margin:0; font-size: 10px; color: #4b5563; font-weight:600;">PVC, ALÜMİNYUM & CAM BALKON SİSTEMLERİ</p>
                </div>
                <div style="text-align: right;">
                    <h3 style="margin:0; color: #0F2C59; letter-spacing: 1px;">FİYAT TEKLİF FORMU</h3>
                    <p style="margin:2px 0 0 0; font-size: 11px; color: #6b7280;"><b>Teklif No:</b> {tf_no}</p>
                    <p style="margin:0; font-size: 11px; color: #6b7280;"><b>Tarih:</b> {tf_tarih.strftime('%d.%m.%Y')}</p>
                </div>
            </div>
            
            <!-- MÜŞTERİ BİLGİLERİ -->
            <div style="background-color: #f8fafc; border-left: 4px solid #0F2C59; padding: 10px 12px; margin-bottom: 15px; border-radius: 0 4px 4px 0;">
                <p style="margin:0; font-size: 12px;"><b>Sayın / Firma:</b> {tf_musteri}</p>
                <p style="margin:2px 0 0 0; font-size: 12px;"><b>İlgili Kişi:</b> {tf_yetkili} | <b>Tel:</b> {tf_tel}</p>
            </div>
            
            <!-- KALEMLER TABLOSU -->
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                <thead>
                    <tr style="background-color: #0F2C59; color: #ffffff; font-size: 12px;">
                        <th style="padding: 8px; width: 5%;">#</th>
                        <th style="padding: 8px; text-align: left;">Ürün / Hizmet Açıklaması</th>
                        <th style="padding: 8px; text-align: center; width: 15%;">Miktar</th>
                        <th style="padding: 8px; text-align: right; width: 20%;">Birim Fiyat</th>
                        <th style="padding: 8px; text-align: right; width: 20%;">Toplam Tutar</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_html if table_rows_html else '<tr><td colspan="5" style="padding:15px; text-align:center; color:#999; font-size:12px;">Henüz kalem eklenmedi.</td></tr>'}
                </tbody>
            </table>
            
            <!-- TOPLAMLAR -->
            <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
                <div style="width: 250px; background-color: #f1f5f9; padding: 10px; border-radius: 4px; text-align: right; font-size: 12px;">
                    <p style="margin: 2px 0; color: #475569;">Ara Toplam: <b>{ara_toplam:,.2f} TL</b></p>
                    <p style="margin: 2px 0; color: #475569;">KDV (%20): <b>{kdv_tutar:,.2f} TL</b></p>
                    <div style="border-top: 2px solid #0F2C59; margin-top: 4px; padding-top: 4px;">
                        <span style="font-size: 14px; font-weight: bold; color: #0F2C59;">GENEL TOPLAM:<br>{genel_toplam:,.2f} TL</span>
                    </div>
                </div>
            </div>
            
            <!-- ŞARTLAR VE İMZA -->
            <div style="margin-top: 20px; border-top: 1px solid #e2e8f0; padding-top: 10px;">
                <h5 style="margin:0 0 5px 0; color: #0F2C59; font-size:12px;">TEKLİF KOŞULLARI & ŞARTLAR</h5>
                <div style="font-size: 10px; color: #475569; line-height: 1.4; background-color: #fafafa; padding: 8px; border-radius: 4px;">
                    {formatted_sartlar}
                </div>
            </div>
            
            <div style="display: flex; justify-content: space-between; margin-top: 30px; text-align: center; font-size: 11px; color: #334155;">
                <div style="width: 40%;">
                    <p style="margin-bottom: 35px;"><b>ART DİZAYN</b><br>Yetkili İmza / Kaşe</p>
                    <p>_______________________</p>
                </div>
                <div style="width: 40%;">
                    <p style="margin-bottom: 35px;"><b>MÜŞTERİ ONAYI</b><br>İmza / Tarih</p>
                    <p>_______________________</p>
                </div>
            </div>
        </div>
        """
        
        st.markdown(teklif_html_full, unsafe_allow_html=True)
        st.info("💡 **PDF Olarak Kaydetme:** Klavyenizden **Ctrl + P** yapıp hedefi *PDF Olarak Kaydet* seçebilirsiniz.")

# ---------------------------------------------------------
# DİĞER SEKMELER (MÜŞTERİ, ÖLÇÜ, PROFORMA, TAKVİM, STOK)
# ---------------------------------------------------------
with tab_musteri:
    st.subheader("👤 Müşteri Cari Yönetimi ve Arama")
    c_m1, c_m2 = st.columns([1, 2])
    with c_m1:
        f_adi = st.text_input("Firma / Müşteri Adı")
        y_adi = st.text_input("Yetkili Adı")
        tel = st.text_input("Telefon", "+905321112233")
        adr = st.text_area("Adres")
        if st.button("💾 Müşteriyi Kaydet", use_container_width=True):
            if f_adi:
                c.execute("INSERT INTO musteriler (firma_adi, yetkili, telefon, adres) VALUES (?, ?, ?, ?)", (f_adi, y_adi, tel, adr))
                conn.commit()
                st.rerun()
    with c_m2:
        arama = st.text_input("🔍 Müşteri Arama:")
        if arama:
            res = pd.read_sql_query(f"SELECT * FROM musteriler WHERE firma_adi LIKE '%{arama}%' OR yetkili LIKE '%{arama}%'", conn)
            st.dataframe(res, use_container_width=True)

with tab_hesap:
    st.subheader("📏 En x Boy Ölçüsünden Otomatik Profil ve Cam Hesabı")
    en_cm = st.number_input("En Ölçüsü (cm)", value=200.0)
    boy_cm = st.number_input("Boy Ölçüsü (cm)", value=150.0)
    st.write(f"Net Alan: {(en_cm/100)*(boy_cm/100):.2f} m²")

with tab_proforma:
    st.subheader("📑 PROFORMA FATURA VE WHATSAPP TEKLİFİ")
    p_mus = st.text_input("Müşteri Adı", "Ahmet Yılmaz")
    p_tel = st.text_input("WhatsApp Telefon (+90...)", "+905320000000")
    p_is = st.text_input("İş Açıklaması", "Cam Balkon Kapatma")
    p_tutar = st.number_input("Toplam İş Bedeli (TL)", value=38400.0)
    wa_mesaj = f"Sayın {p_mus},\nART DİZAYN teklif detayınız:\nİş: {p_is}\nTutar: {p_tutar:,.2f} TL"
    wa_link = f"https://wa.me/{p_tel.replace('+','').replace(' ','')}?text={urllib.parse.quote(wa_mesaj)}"
    st.markdown(f"[📲 WHATSAPP İLE TEKLİF GÖNDER]({wa_link})")

with tab_takvim:
    st.subheader("🗓️ Şantiye & Montaj Planlayıcısı")
    df_plan = pd.read_sql_query("SELECT isin_cinsi, toplam_tutar, montaj_tarihi FROM isler WHERE montaj_tarihi IS NOT NULL ORDER BY montaj_tarihi ASC", conn)
    st.dataframe(df_plan, use_container_width=True)

with tab_stok:
    st.subheader("📦 Tedarikçi Depo & Stok Yönetimi")
    df_stok = pd.read_sql_query("SELECT * FROM stok", conn)
    st.dataframe(df_stok, use_container_width=True)
