import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
from datetime import datetime, date, timedelta
from io import BytesIO

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

st.set_page_config(page_title="ART DİZAYN Kurumsal ERP", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
@media (max-width: 768px) {
    .stButton button { width: 100% !important; margin-bottom: 4px; }
    [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
}
.st-borclu { background-color: #fee2e2; border-left: 5px solid #ef4444; padding: 12px; border-radius: 6px; color: #991b1b; }
.st-temiz { background-color: #dcfce7; border-left: 5px solid #22c55e; padding: 12px; border-radius: 6px; color: #166534; }
.st-alert { background-color: #fef3c7; border-left: 5px solid #f59e0b; padding: 12px; border-radius: 6px; color: #92400e; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# Veritabanı Mimarisi (SQLite Full Entegre)
conn = sqlite3.connect('art_dizayn_full_erp_v2.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS musteriler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, firma_adi TEXT, yetkili TEXT, telefon TEXT, adres TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tedarikciler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, unvan TEXT, telefon TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS teklifler 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, teklif_no TEXT, musteri_id INTEGER, tedarikci_id INTEGER, 
              isin_cinsi TEXT, miktar REAL, birim TEXT, detaylar TEXT, birim_fiyat REAL, toplam_tutar REAL, 
              maliyet REAL, durum TEXT DEFAULT 'Beklemede', montaj_tarihi TEXT, tarih TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS kasa_hareket 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, tip TEXT, kategori TEXT, musteri_id INTEGER, tedarikci_id INTEGER,
              eleman_id INTEGER, tutar REAL, tarih TEXT, aciklama TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS borclar 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, kurum_adi TEXT, tip TEXT, toplam_borc REAL, odenen_borc REAL, taksit_sayisi INTEGER, vade_tarihi TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS elemanlar 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, ad_soyad TEXT, unvan TEXT, maas REAL, hakedis REAL, odenen REAL)''')

conn.commit()

# PDF Oluşturma Motoru
def make_pdf(m_adi, is_cinsi, miktar, birim, detay, birim_fiyat, toplam, teklif_no):
    if not HAS_FPDF: return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="ART DIZAYN - TEKLIF FORMU", ln=1, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 8, txt=f"Teklif No: {teklif_no} | Tarih: {datetime.now().strftime('%d.%m.%Y')}", ln=1, align="C")
    pdf.ln(5)
    pdf.cell(190, 8, txt=f"Musteri: {m_adi}", ln=1)
    pdf.cell(190, 8, txt=f"Isin Cinsi: {is_cinsi}", ln=1)
    pdf.cell(190, 8, txt=f"Miktar: {miktar} {birim}", ln=1)
    pdf.cell(190, 8, txt=f"Birim Fiyat: {birim_fiyat:,.2f} TL", ln=1)
    pdf.cell(190, 8, txt=f"Toplam Tutar: {toplam:,.2f} TL", ln=1)
    pdf.ln(5)
    pdf.multi_cell(190, 5, txt=f"Is Detaylari:\n{detay}")
    return pdf.output(dest='S').encode('latin-1', 'replace')

st.title("🏗️ ART DİZAYN - Tam Kapsamlı Entegre ERP")

# ---------------------------------------------------------
# AKILLI HATIRLATMA PANENLİ (ALERT DASHBOARD)
# ---------------------------------------------------------
bugun = date.today().strftime('%Y-%m-%d')
yakin_tarih = (date.today() + timedelta(days=3)).strftime('%Y-%m-%d')

df_alert = pd.read_sql_query("""
    SELECT t.teklif_no, m.firma_adi, t.isin_cinsi, t.montaj_tarihi 
    FROM teklifler t 
    JOIN musteriler m ON t.musteri_id = m.id 
    WHERE t.durum='Onaylandı' AND t.montaj_tarihi <= ?
""", conn, params=(yakin_tarih,))

if not df_alert.empty:
    st.markdown(f"""<div class="st-alert">
        <h4>⚠️ MONTAJ VE TESLİMAT HATIRLATICI ({len(df_alert)} İŞ)</h4>
        <p>Önümüzdeki 3 gün içinde montajı yaklaşan veya tarihi geçen işleriniz bulunmaktadır:</p>
    </div>""", unsafe_allow_html=True)
    st.dataframe(df_alert, use_container_width=True)

# ---------------------------------------------------------
# TABLAR
# ---------------------------------------------------------
tab_musteri, tab_kasa, tab_borc, tab_eleman, tab_tedarikci = st.tabs([
    "👤 Müşteriler & Teklif Yönetimi",
    "💰 Kasa & Tahsilat Defteri",
    "🏦 Borç, Banka & Taksit Takibi",
    "👷 Eleman Maaş & Prim Çizelgesi",
    "🏭 Tedarikçi Cari Yönetimi"
])

# ---------------------------------------------------------
# 1. MÜŞTERİ ÖZEL SAYFASI & TEKLİF YÖNETİMİ
# ---------------------------------------------------------
with tab_musteri:
    st.subheader("👤 Müşteri Cari Ekstrası & İş Girişi")
    col_m1, col_m2 = st.columns([1, 2])
    
    with col_m1:
        st.write("### ➕ Yeni Müşteri Ekle")
        m_firma = st.text_input("Firma / Müşteri Adı*")
        m_yetkili = st.text_input("Yetkili Adı")
        m_tel = st.text_input("Telefon", "+90 532 000 00 00")
        m_adr = st.text_area("Adres")
        
        if st.button("💾 Müşteriyi Ekle", use_container_width=True):
            if m_firma.strip():
                c.execute("INSERT INTO musteriler (firma_adi, yetkili, telefon, adres) VALUES (?, ?, ?, ?)", (m_firma, m_yetkili, m_tel, m_adr))
                conn.commit()
                st.success("Müşteri veritabanına eklendi!")
                st.rerun()

    with col_m2:
        df_m = pd.read_sql_query("SELECT id, firma_adi FROM musteriler", conn)
        df_ted = pd.read_sql_query("SELECT id, unvan FROM tedarikciler", conn)
        
        if not df_m.empty:
            sel_m_id = st.selectbox("Müşteri Seçin", df_m['id'].tolist(), format_func=lambda x: df_m[df_m['id']==x]['firma_adi'].values[0])
            
            # Finansal Durum Hesabı
            df_borc_sum = pd.read_sql_query("SELECT SUM(toplam_tutar) as t FROM teklifler WHERE musteri_id=? AND durum='Onaylandı'", conn, params=(sel_m_id,))
            toplam_borc = df_borc_sum['t'].iloc[0] if df_borc_sum['t'].iloc[0] else 0.0
            
            df_tahs_sum = pd.read_sql_query("SELECT SUM(tutar) as t FROM kasa_hareket WHERE musteri_id=? AND tip='Gelir'", conn, params=(sel_m_id,))
            toplam_tahs = df_tahs_sum['t'].iloc[0] if df_tahs_sum['t'].iloc[0] else 0.0
            
            bakiye = toplam_borc - toplam_tahs
            
            if bakiye > 0:
                st.markdown(f"""<div class="st-borclu">
                    <h3>🔴 BORÇLU MÜŞTERİ | KALAN BORÇ: {bakiye:,.2f} TL</h3>
                    <p>Toplam Onaylı İş: {toplam_borc:,.2f} TL | Toplam Tahsilat: {toplam_tahs:,.2f} TL</p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="st-temiz">
                    <h3>🟢 BORCU YOK / BAKİYE TEMİZ | BAKİYE: {bakiye:,.2f} TL</h3>
                    <p>Toplam Onaylı İş: {toplam_borc:,.2f} TL | Toplam Tahsilat: {toplam_tahs:,.2f} TL</p>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.write("### 💵 Müşteriden Tahsilat Al (Kasaya İşler & Borçtan Düşer)")
            c_th1, c_th2 = st.columns(2)
            t_tutar = c_th1.number_input("Tahsilat Tutarı (TL)", value=1000.0, step=500.0)
            t_acik = c_th2.text_input("Tahsilat Açıklaması", "Banka Havalesi / Peşinat")
            
            if st.button("💳 Tahsilatı İşle", use_container_width=True):
                c.execute("INSERT INTO kasa_hareket (tip, kategori, musteri_id, tutar, tarih, aciklama) VALUES ('Gelir', 'Müşteri Tahsilatı', ?, ?, ?, ?)",
                          (sel_m_id, t_tutar, datetime.now().strftime('%Y-%m-%d'), t_acik))
                conn.commit()
                st.success("Tahsilat kasaya işlendi ve müşteri borcundan düşüldü!")
                st.rerun()

            st.markdown("---")
            st.write("### 📝 Yeni Teklif / İş Girişi")
            c_tk1, c_tk2 = st.columns(2)
            is_cinsi = c_tk1.text_input("İşin Cinsi", "Alüminyum Küpeşte & Cam Balkon")
            is_miktari = c_tk2.number_input("Miktar", value=10.0)
            is_birim = c_tk1.selectbox("Birim", ["m²", "Metre", "Adet", "Kg", "Set"])
            is_fiyat = c_tk2.number_input("Birim Satış Fiyatı (TL)", value=3500.0)
            
            is_maliyet = c_tk1.number_input("Tahmini Malzeme Maliyeti (TL)", value=15000.0)
            
            ted_id = None
            if not df_ted.empty:
                ted_id = c_tk2.selectbox("Malzeme Tedarikçisi Seçin", [None] + df_ted['id'].tolist(), 
                                         format_func=lambda x: "Seçilmedi" if x is None else df_ted[df_ted['id']==x]['unvan'].values[0])
            
            is_detay = st.text_area("İş Detayları", "Profil serisi: 50'lik ısı yalıtımlı. Montaj dahil.")
            toplam_fiyat = is_miktari * is_fiyat
            
            st.info(f"Hesaplanan Toplam Teklif Tutarı: **{toplam_fiyat:,.2f} TL**")
            
            c_s1, c_s2 = st.columns(2)
            if c_s1.button("💾 Teklifi Kaydet", use_container_width=True):
                t_no = f"ART-{datetime.now().strftime('%Y%m%d')}-{len(pd.read_sql_query('SELECT id FROM teklifler', conn))+1:02d}"
                c.execute("""INSERT INTO teklifler 
                    (teklif_no, musteri_id, tedarikci_id, isin_cinsi, miktar, birim, detaylar, birim_fiyat, toplam_tutar, maliyet, tarih) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (t_no, sel_m_id, ted_id, is_cinsi, is_miktari, is_birim, is_detay, is_fiyat, toplam_fiyat, is_maliyet, datetime.now().strftime('%Y-%m-%d')))
                conn.commit()
                st.success("Teklif başarıyla kaydedildi!")
                st.rerun()

            # PDF / Excel İndirme
            m_name_curr = df_m[df_m['id']==sel_m_id]['firma_adi'].values[0]
            ex_buffer = BytesIO()
            pd.DataFrame([{"Müşteri": m_name_curr, "İş": is_cinsi, "Miktar": is_miktari, "Tutar": toplam_fiyat}]).to_excel(ex_buffer, index=False)
            
            c_s2.download_button(
                label="📊 Excel Olarak İndir",
                data=ex_buffer.getvalue(),
                file_name=f"Teklif_{m_name_curr}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # Onaylama & Montaj Hatırlatıcısı
            st.markdown("---")
            st.write("### 📑 Teklif Geçmişi ve Onaylama")
            df_m_tek = pd.read_sql_query("SELECT id, teklif_no, isin_cinsi, toplam_tutar, maliyet, durum, montaj_tarihi FROM teklifler WHERE musteri_id=?", conn, params=(sel_m_id,))
            st.dataframe(df_m_tek, use_container_width=True)
            
            if not df_m_tek.empty:
                sel_t_id = st.selectbox("Onaylanacak Teklif ID", df_m_tek['id'].tolist())
                m_tarih = st.date_input("Montaj Tarihi Belirle", value=date.today())
                
                if st.button("✅ Teklifi Onayla (Borçlandır & Montaj Kur)", use_container_width=True):
                    c.execute("UPDATE teklifler SET durum='Onaylandı', montaj_tarihi=? WHERE id=?", (m_tarih.strftime('%Y-%m-%d'), sel_t_id))
                    
                    # Eğer tedarikçi seçilmişse tedarikçiye borç yaz
                    row_t = df_m_tek[df_m_tek['id']==sel_t_id].iloc[0]
                    if row_t['maliyet'] > 0:
                        c.execute("INSERT INTO borclar (kurum_adi, tip, toplam_borc, odenen_borc, taksit_sayisi, vade_tarihi) VALUES (?, 'Tedarikçi Malzeme', ?, 0, 1, ?)",
                                  (f"İş Maliyeti (Teklif No: {row_t['teklif_no']})", row_t['maliyet'], m_tarih.strftime('%Y-%m-%d')))
                    
                    conn.commit()
                    st.success("Teklif onaylandı! Müşteri borçlandırıldı, tedarikçi maliyeti işlendi ve montaj hatırlatıcı kuruldu.")
                    st.rerun()

# ---------------------------------------------------------
# 2. KASA DEFTERİ
# ---------------------------------------------------------
with tab_kasa:
    st.subheader("💰 Genel Kasa Defteri")
    df_kasa = pd.read_sql_query("SELECT id, tip as 'İşlem', kategori as 'Kategori', tutar as 'Tutar (TL)', tarih as 'Tarih', aciklama as 'Açıklama' FROM kasa_hareket ORDER BY id DESC", conn)
    
    g_toplam = df_kasa[df_kasa['İşlem']=='Gelir']['Tutar (TL)'].sum() if not df_kasa.empty else 0.0
    c_toplam = df_kasa[df_kasa['İşlem']=='Gider']['Tutar (TL)'].sum() if not df_kasa.empty else 0.0
    
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Toplam Tahsilat (Giriş)", f"{g_toplam:,.2f} TL")
    col_k2.metric("Toplam Ödeme (Çıkış)", f"{c_toplam:,.2f} TL")
    col_k3.metric("Net Kasa Bakiyesi", f"{(g_toplam - c_toplam):,.2f} TL")
    
    st.dataframe(df_kasa, use_container_width=True)

# ---------------------------------------------------------
# 3. BORÇ, BANKA VE OTOMATİK TAKSİT PLANI
# ---------------------------------------------------------
with tab_borc:
    st.subheader("🏦 Tedarikçi, Banka & Otomatik Taksit Takibi")
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.write("### ➕ Yeni Borç / Kredi Ekle")
        b_kurum = st.text_input("Kurum / Tedarikçi / Banka")
        b_tip = st.selectbox("Borç Tipi", ["Tedarikçi Borcu", "Banka Kredisi", "Kredi Kartı Taksiti", "Devlet / Vergi / SGK"])
        b_tutar = st.number_input("Toplam Tutar (TL)", value=30000.0, step=1000.0)
        b_taksit = st.number_input("Taksit Sayısı", value=3, min_value=1)
        b_vade = st.date_input("İlk Taksit / Vade Tarihi", value=date.today())
        
        if st.button("💾 Borç / Taksit Planı Oluştur", use_container_width=True):
            c.execute("INSERT INTO borclar (kurum_adi, tip, toplam_borc, odenen_borc, taksit_sayisi, vade_tarihi) VALUES (?, ?, ?, 0, ?, ?)",
                      (b_kurum, b_tip, b_tutar, b_taksit, b_vade.strftime('%Y-%m-%d')))
            conn.commit()
            st.success("Borç ve taksit planı oluşturuldu!")
            st.rerun()

    with col_b2:
        df_b = pd.read_sql_query("SELECT id, kurum_adi as 'Kurum', tip as 'Tip', toplam_borc as 'Toplam Borç', odenen_borc as 'Ödenen', taksit_sayisi as 'Taksit', vade_tarihi as 'Vade' FROM borclar", conn)
        
        if not df_b.empty:
            df_b['Kalan Borç'] = df_b['Toplam Borç'] - df_b['Ödenen']
            df_b['Aylık Taksit'] = df_b['Kalan Borç'] / df_b['Taksit']
            st.dataframe(df_b, use_container_width=True)
            
            st.markdown("---")
            st.write("### 💳 Taksit / Borç Ödemesi Yap (Kasadan Düşer)")
            sel_b = st.selectbox("Ödenecek Borç ID", df_b['id'].tolist())
            o_tutar = st.number_input("Ödeme Tutarı (TL)", value=5000.0, step=500.0)
            
            if st.button("💸 Ödemeyi Gerçekleştir", use_container_width=True):
                c.execute("UPDATE borclar SET odenen_borc = odenen_borc + ? WHERE id=?", (o_tutar, sel_b))
                b_kname = df_b[df_b['id']==sel_b]['Kurum'].values[0]
                c.execute("INSERT INTO kasa_hareket (tip, kategori, tutar, tarih, aciklama) VALUES ('Gider', 'Borç/Taksit Ödemesi', ?, ?, ?)",
                          (o_tutar, datetime.now().strftime('%Y-%m-%d'), f"{b_kname} Borç Ödemesi"))
                conn.commit()
                st.success("Borç ödemesi yapıldı ve kasadan düşüldü!")
                st.rerun()

# ---------------------------------------------------------
# 4. ELEMAN MAAŞ, HAKEDİŞ & PRİM
# ---------------------------------------------------------
with tab_eleman:
    st.subheader("👷 Eleman Maaş, Mesai & Prim Çizelgesi")
    col_e1, col_e2 = st.columns([1, 2])
    
    with col_e1:
        st.write("### ➕ Eleman Ekle")
        e_ad = st.text_input("Eleman Ad Soyad")
        e_unvan = st.text_input("Görev / Unvan", "Montaj Ustası")
        e_maas = st.number_input("Sabit Maaş (TL)", value=25000.0, step=1000.0)
        
        if st.button("👷 Elemanı Kaydet", use_container_width=True):
            if e_ad.strip():
                c.execute("INSERT INTO elemanlar (ad_soyad, unvan, maas, hakedis, odenen) VALUES (?, ?, ?, ?, 0)", (e_ad, e_unvan, e_maas, e_maas))
                conn.commit()
                st.success("Eleman eklendi!")
                st.rerun()

    with col_e2:
        df_e = pd.read_sql_query("SELECT id, ad_soyad as 'Ad Soyad', unvan as 'Unvan', maas as 'Sabit Maaş', hakedis as 'Toplam Hakediş', odenen as 'Ödenen' FROM elemanlar", conn)
        
        if not df_e.empty:
            df_e['Kalan Alacak'] = df_e['Toplam Hakediş'] - df_e['Ödenen']
            st.dataframe(df_e, use_container_width=True)
            
            st.markdown("---")
            c_p1, c_p2 = st.columns(2)
            sel_e = c_p1.selectbox("Eleman Seçin", df_e['id'].tolist())
            
            st.write("**➕ Ekstra Prim / Montaj Hakedişi Ekle**")
            p_tutar = c_p1.number_input("Ekstra Prim/Mesai Tutarı (TL)", value=1500.0, step=250.0)
            if c_p1.button("➕ Hakedişe Ekle", use_container_width=True):
                c.execute("UPDATE elemanlar SET hakedis = hakedis + ? WHERE id=?", (p_tutar, sel_e))
                conn.commit()
                st.success("Prim/Hakediş elemana eklendi!")
                st.rerun()

            st.write("**💸 Ödeme Yap (Kasadan Çıkar)**")
            e_odeme = c_p2.number_input("Ödenecek Avans / Maaş (TL)", value=3000.0, step=500.0)
            if c_p2.button("💸 Elemana Öde", use_container_width=True):
                c.execute("UPDATE elemanlar SET odenen = odenen + ? WHERE id=?", (e_odeme, sel_e))
                ename = df_e[df_e['id']==sel_e]['Ad Soyad'].values[0]
                c.execute("INSERT INTO kasa_hareket (tip, kategori, eleman_id, tutar, tarih, aciklama) VALUES ('Gider', 'Eleman Ödemesi', ?, ?, ?, ?)",
                          (sel_e, e_odeme, datetime.now().strftime('%Y-%m-%d'), f"{ename} Maaş/Avans"))
                conn.commit()
                st.success("Ödeme yapıldı ve kasadan düşüldü!")
                st.rerun()

# ---------------------------------------------------------
# 5. TEDARİKÇİ CARİ YÖNETİMİ
# ---------------------------------------------------------
with tab_tedarikci:
    st.subheader("🏭 Tedarikçi Firmalar ve Malzeme Borçları")
    col_td1, col_td2 = st.columns([1, 2])
    
    with col_td1:
        st.write("### ➕ Yeni Tedarikçi Ekle")
        t_unvan = st.text_input("Tedarikçi Firma Adı", "Asaş Alüminyum A.Ş.")
        t_tel = st.text_input("Tedarikçi Telefon", "+90 212 000 00 00")
        
        if st.button("💾 Tedarikçiyi Kaydet", use_container_width=True):
            if t_unvan.strip():
                c.execute("INSERT INTO tedarikciler (unvan, telefon) VALUES (?, ?)", (t_unvan, t_tel))
                conn.commit()
                st.success("Tedarikçi eklendi!")
                st.rerun()

    with col_td2:
        df_ted_list = pd.read_sql_query("SELECT id as 'ID', unvan as 'Firma Unvanı', telefon as 'Telefon' FROM tedarikciler", conn)
        st.dataframe(df_ted_list, use_container_width=True)
