import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import time
import pandas as pd

# --- 1. MENGHUBUNGKAN KE AWAN FIREBASE (DENGAN KUNCI GANDA) ---
if not firebase_admin._apps:
    try:
        # Coba buka pakai kunci Brankas Rahasia internet dulu
        try:
            kunci_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(kunci_dict)
        except:
            # Kalau tidak ada, berarti masih di laptop, pakai file firebasekey.json
            cred = credentials.Certificate("firebasekey.json")
            
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://water-monitoring-system-e890a-default-rtdb.asia-southeast1.firebasedatabase.app/'
        })
    except Exception as e:
        st.error(f"Yah, gagal terhubung ke awan: {e}")

st.set_page_config(page_title="Markas Air Pintar", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1E88E5;'>💧 Water Monitoring System 💧</h1>", unsafe_allow_html=True)
st.write("<p style='text-align: center;'>Your Monitoring Assistant</p>", unsafe_allow_html=True)

# --- 2. RUANG KENDALI TANGAN (3 TOMBOL VALVE) ---
st.subheader("🎮 Ruang Kendali Pintu Air (Valve Tiap Lantai)")

# Membaca status ketiga Valve dari awan
ref_kontrol = db.reference('/Test_Distribusi/Kontrol')
data_kontrol = ref_kontrol.get()

# Kalau belum ada datanya sama sekali, kita anggap kosong dulu
if data_kontrol is None:
    data_kontrol = {}

status_v1 = data_kontrol.get('Valve_Lantai_1', 'TUTUP')
status_v2 = data_kontrol.get('Valve_Lantai_2', 'TUTUP')
status_v3 = data_kontrol.get('Valve_Lantai_3', 'TUTUP')

# Menampilkan 3 tombol berjajar
kolom_v1, kolom_v2, kolom_v3 = st.columns(3)

# Tombol Lantai 1
with kolom_v1:
    st.markdown("### 🏢 Lantai 1")
    if st.button("🔄 Ubah Pintu Lantai 1", key="btn_v1"):
        posisi_baru = 'BUKA' if status_v1 == 'TUTUP' else 'TUTUP'
        ref_kontrol.update({'Valve_Lantai_1': posisi_baru})
        st.rerun()
        
    if status_v1 == 'BUKA':
        st.success("Status: **TERBUKA** 🟢")
    else:
        st.error("Status: **TERTUTUP** 🔴")

# Tombol Lantai 2
with kolom_v2:
    st.markdown("### 🏢 Lantai 2")
    if st.button("🔄 Ubah Pintu Lantai 2", key="btn_v2"):
        posisi_baru = 'BUKA' if status_v2 == 'TUTUP' else 'TUTUP'
        ref_kontrol.update({'Valve_Lantai_2': posisi_baru})
        st.rerun()
        
    if status_v2 == 'BUKA':
        st.success("Status: **TERBUKA** 🟢")
    else:
        st.error("Status: **TERTUTUP** 🔴")

# Tombol Lantai 3
with kolom_v3:
    st.markdown("### 🏢 Lantai 3")
    if st.button("🔄 Ubah Pintu Lantai 3", key="btn_v3"):
        posisi_baru = 'BUKA' if status_v3 == 'TUTUP' else 'TUTUP'
        ref_kontrol.update({'Valve_Lantai_3': posisi_baru})
        st.rerun()
        
    if status_v3 == 'BUKA':
        st.success("Status: **TERBUKA** 🟢")
    else:
        st.error("Status: **TERTUTUP** 🔴")

st.divider()

# --- 3. LAYAR PEMANTAU OTOMATIS ---
layar_utama = st.empty()

while True:
    ref = db.reference('/Test_Distribusi')
    data = ref.get()

    if data is None:
        data = {}

    with layar_utama.container():
        # --- MENGAMBIL DATA WATERFLOW ---
        s1 = data.get('Sensor_1', {})
        s2 = data.get('Sensor_2', {})
        s3 = data.get('Sensor_3', {})
        s4 = data.get('Sensor_4', {})
        s5 = data.get('Sensor_5', {})
        s6 = data.get('Sensor_6', {})
        s7 = data.get('Sensor_7', {})

        # --- MENGAMBIL DATA SENSOR BARU ---
        data_kualitas = data.get('Kualitas_Air', {})
        tds_atas = data_kualitas.get('TDS_Atas', 0)
        tds_bawah = data_kualitas.get('TDS_Bawah', 0)
        suhu_air = data_kualitas.get('Suhu', 0.0)

        data_jarak = data.get('Ultrasonik', {})
        tinggi_atas = data_jarak.get('Toren_Atas', 0)
        tinggi_bawah = data_jarak.get('Toren_Bawah', 0)

        data_mesin = data.get('Mesin_Pompa', {})
        pompa_naik = data_mesin.get('Pompa_ke_Atas', 'MATI')
        pompa_pdam = data_mesin.get('Pompa_PDAM', 'MATI')

        # === MENAMPILKAN DI LAYAR ===
        
        # BARIS 1: Gedung
        st.subheader("🏢 Air di Dalam Gedung (Pemakaian)")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Lantai 1", f"{s1.get('Kecepatan', 0):.2f} L/min", f"{s1.get('Volume', 0):.2f} Liter")
        k2.metric("Lantai 2", f"{s2.get('Kecepatan', 0):.2f} L/min", f"{s2.get('Volume', 0):.2f} Liter")
        k3.metric("Lantai 3", f"{s3.get('Kecepatan', 0):.2f} L/min", f"{s3.get('Volume', 0):.2f} Liter")
        k4.metric("Keluar Toren Atas", f"{s4.get('Kecepatan', 0):.2f} L/min", f"{s4.get('Volume', 0):.2f} Liter")

        # BARIS 2: Pengisian ke Toren Atas
        st.subheader("⬆️ Jalur Pengisian Toren Atas")
        k5, k6 = st.columns(2)
        k5.metric("Pipa A (Dari Toren Bawah)", f"{s5.get('Kecepatan', 0):.2f} L/min", f"{s5.get('Volume', 0):.2f} Liter")
        k6.metric("Pipa B (Sampai di Atas)", f"{s6.get('Kecepatan', 0):.2f} L/min", f"{s6.get('Volume', 0):.2f} Liter")

        # BARIS 3: PDAM
        st.subheader("💧 Sumber Air PDAM (Pengisian Toren Bawah)")
        k7, k_kosong = st.columns(2)
        k7.metric("Air Masuk dari PDAM", f"{s7.get('Kecepatan', 0):.2f} L/min", f"{s7.get('Volume', 0):.2f} Liter")

        st.divider()

        # BARIS 4: Ketinggian Air (Ultrasonik) & Mesin Pompa
        st.subheader("📏 Status Toren & Mesin Air")
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("Isi Toren Bawah", f"{tinggi_bawah} cm")
        t2.metric("Isi Toren Atas", f"{tinggi_atas} cm")
        
        if pompa_pdam == 'NYALA':
            t3.success("Mesin PDAM: **NYALA** 🟢")
        else:
            t3.error("Mesin PDAM: **MATI** 🔴")
            
        if pompa_naik == 'NYALA':
            t4.success("Mesin Pompa Naik: **NYALA** 🟢")
        else:
            t4.error("Mesin Pompa Naik: **MATI** 🔴")

        st.divider()

        # BARIS 5: Kualitas & Suhu Air
        st.subheader("🔬 Pemeriksaan Kualitas Air")
        q1, q2, q3 = st.columns(3)
        q1.metric("Kotoran Toren Bawah (TDS)", f"{tds_bawah} ppm")
        q2.metric("Kotoran Toren Atas (TDS)", f"{tds_atas} ppm")
        q3.metric("Suhu Air", f"{suhu_air} °C")
        
        st.divider()

        # --- BARIS 6: ALARM DETEKTIF KEBOCORAN! ---
        st.subheader("🚨 Alarm Kebocoran Pipa")
        
        kolom_alarm1, kolom_alarm2 = st.columns(2)
        
        with kolom_alarm1:
            # Mengecek jalur toren ke lantai bawah
            air_dipakai = s1.get('Kecepatan', 0) + s2.get('Kecepatan', 0) + s3.get('Kecepatan', 0)
            air_keluar_toren = s4.get('Kecepatan', 0)
            air_hilang_gedung = air_keluar_toren - air_dipakai
            
            if air_hilang_gedung > 0.5:
                st.error(f"Gawat! Ada air yang tumpah {air_hilang_gedung:.2f} Liter/menit di pipa dalam gedung! 💦")
            else:
                st.success("Hore! Pipa dalam gedung sangat aman. ✅")
                
        with kolom_alarm2:
            # Mengecek jalur pengisian (Pipa A vs Pipa B)
            air_bawah = s5.get('Kecepatan', 0)
            air_atas = s6.get('Kecepatan', 0)
            air_hilang_pengisian = air_bawah - air_atas
            
            if air_hilang_pengisian > 0.5:
                st.error(f"Gawat! Ada air yang tumpah {air_hilang_pengisian:.2f} Liter/menit saat naik ke toren atas! 💦")
            else:
                st.success("Hore! Pipa yang naik ke toren aman. ✅")

    # Layar berkedip memperbarui data setiap 1 detik
    time.sleep(1)