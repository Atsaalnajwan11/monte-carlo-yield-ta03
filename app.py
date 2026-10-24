"""
================================================================================
APLIKASI WEB MONTE CARLO SIMULATION - ESTIMASI RISIKO YIELD PADI INDONESIA
================================================================================
Tugas Akhir 03 (TA-03) - Pemodelan dan Simulasi
Mahasiswa: Atsaal Najwan (NIM 301240012)

Cara menjalankan (lokal):
    streamlit run app.py

Cara deploy:
    Lihat README.md
================================================================================
"""

import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import os

# ============================================================
# KONFIGURASI HALAMAN
# ============================================================
st.set_page_config(
    page_title="Monte Carlo - Yield Padi Indonesia",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS UNTUK STYLING
# ============================================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2e86c1);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
    }
    .main-header p {
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
        opacity: 0.9;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2e86c1;
        margin-bottom: 0.5rem;
    }
    .risk-low { color: #27ae60; }
    .risk-moderate { color: #f39c12; }
    .risk-high { color: #e74c3c; }
    .stButton > button {
        background: linear-gradient(90deg, #2e86c1, #1f4e79);
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER UTAMA
# ============================================================
st.markdown("""
<div class="main-header">
    <h1>🌾 Simulasi Monte Carlo - Yield Padi Indonesia</h1>
    <p>TA-03 Pemodelan & Simulasi | Data-Driven Risk Assessment</p>
    <p style="font-size:0.8rem; opacity:0.8;">Atsaal Najwan (NIM 301240012)</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR - PENGATURAN
# ============================================================
st.sidebar.markdown("## ⚙️ Pengaturan Simulasi")
st.sidebar.markdown("---")

# Pilihan input data
input_mode = st.sidebar.radio(
    "📂 Sumber Data:",
    ["Upload CSV Sendiri", "Gunakan yield_df.csv (Default)"],
    index=1,
)

# Filter area dan item
default_country = "Indonesia"
default_item = "Rice, paddy"

if input_mode == "Upload CSV Sendiri":
    uploaded_file = st.sidebar.file_uploader(
        "Upload file CSV", type=['csv']
    )
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.sidebar.success(f"✓ File dimuat: {uploaded_file.name}")
    else:
        st.sidebar.info("⏳ Menunggu upload CSV...")
        st.stop()
else:
    # Cari file yield_df.csv di beberapa lokasi
    possible_paths = [
        'yield_df.csv',
        './yield_df.csv',
        '../yield_df.csv',
        'data/yield_df.csv',
        os.path.join(os.path.dirname(__file__), 'yield_df.csv'),
    ]
    csv_path = None
    for p in possible_paths:
        if os.path.exists(p):
            csv_path = p
            break

    if csv_path:
        df = pd.read_csv(csv_path)
        st.sidebar.success(f"✓ yield_df.csv dimuat ({len(df)} baris)")
    else:
        st.sidebar.warning("⚠️ File yield_df.csv tidak ditemukan. Upload manual.")
        uploaded_file = st.sidebar.file_uploader(
            "Upload yield_df.csv", type=['csv']
        )
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        else:
            st.error("❌ Dataset yield_df.csv tidak tersedia. Silakan upload file CSV.")
            st.stop()

# Filter negara & tanaman (jika kolom ada)
if 'Area' in df.columns and 'Item' in df.columns:
    countries = sorted(df['Area'].unique().tolist())
    items = sorted(df['Item'].unique().tolist())

    try:
        default_country_idx = countries.index("Indonesia")
    except ValueError:
        default_country_idx = 0

    try:
        default_item_idx = items.index("Rice, paddy")
    except ValueError:
        default_item_idx = 0

    selected_country = st.sidebar.selectbox(
        "🌍 Pilih Negara:", countries, index=default_country_idx
    )
    selected_item = st.sidebar.selectbox(
        "🌱 Pilih Tanaman:", items, index=default_item_idx
    )

    df_filtered = df[
        (df['Area'] == selected_country) &
        (df['Item'] == selected_item)
    ].copy()
else:
    df_filtered = df.copy()
    selected_country = "Dataset"
    selected_item = "All"

# Slider parameter simulasi
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎲 Parameter Simulasi")

NIM_input = st.sidebar.number_input(
    "🔑 NIM (sebagai Seed):",
    min_value=100000000,
    max_value=999999999,
    value=301240012,
    help="NIM digunakan sebagai seed generator untuk reproducibility."
)

n_iterations = st.sidebar.slider(
    "🔁 Jumlah Iterasi:",
    min_value=1000,
    max_value=50000,
    value=10000,
    step=1000,
    help="Jumlah skenario simulasi. Minimal 5.000 sesuai syarat TA-03."
)

n_lahan = st.sidebar.slider(
    "🏞️ Jumlah Lahan:",
    min_value=10,
    max_value=500,
    value=100,
    step=10,
    help="Jumlah lahan untuk skenario agregat."
)

threshold_pct = st.sidebar.slider(
    "⚠️ Threshold Risiko (% dari Mean):",
    min_value=70,
    max_value=100,
    value=90,
    step=1,
    help="Threshold risiko sebagai persentase dari mean. Default 90% = turun 10%."
)


# ============================================================
# TOMBOL RUN SIMULASI
# ============================================================
st.sidebar.markdown("---")
run_sim = st.sidebar.button("🚀 Jalankan Simulasi", use_container_width=True)


# ============================================================
# FUNGSI SIMULASI MONTE CARLO
# ============================================================
@st.cache_data
def run_monte_carlo(df_input, country, item, nim, n_iter, n_lahan_local, threshold_percent):
    """Jalankan simulasi Monte Carlo dan return hasil"""
    # Filter data
    if 'Area' in df_input.columns and 'Item' in df_input.columns:
        df_sub = df_input[
            (df_input['Area'] == country) &
            (df_input['Item'] == item)
        ].copy()
    else:
        df_sub = df_input.copy()

    if len(df_sub) == 0:
        return None

    # Agregasi per tahun jika ada kolom Year
    if 'Year' in df_sub.columns:
        df_yearly = df_sub.groupby('Year').agg({
            'hg/ha_yield': 'mean'
        }).reset_index()
    else:
        df_yearly = df_sub.copy()
        df_yearly['hg/ha_yield'] = df_yearly.iloc[:, 0]  # kolom pertama sebagai yield

    yields = df_yearly['hg/ha_yield'].values
    n_data = len(yields)

    # Hitung parameter
    mu = float(np.mean(yields))
    sigma = float(np.std(yields, ddof=1))
    min_y = float(np.min(yields))
    max_y = float(np.max(yields))
    cv = sigma / mu * 100

    # Uji normalitas Shapiro-Wilk
    if n_data >= 3:
        try:
            stat_sw, p_sw = stats.shapiro(yields)
        except Exception:
            stat_sw, p_sw = 0, 0
    else:
        stat_sw, p_sw = 0, 0

    # Set seed
    np.random.seed(int(nim))

    # Simulasi 1 lahan
    sim_single = np.random.normal(mu, sigma, n_iter)
    sim_single = np.maximum(sim_single, 0)

    # Simulasi total n lahan
    sim_total = np.random.normal(mu, sigma, size=(n_iter, n_lahan_local)).sum(axis=1)
    sim_total = np.maximum(sim_total, 0)

    # Threshold
    threshold_value = mu * (threshold_percent / 100)
    target_total = mu * n_lahan_local * (threshold_percent / 100)

    # Probabilitas risiko
    prob_drop = float(np.mean(sim_single < threshold_value) * 100)
    prob_below_min = float(np.mean(sim_single < min_y) * 100)
    prob_total_fail = float(np.mean(sim_total < target_total) * 100)

    # Konvergensi
    sample_sizes = np.linspace(100, n_iter, 50, dtype=int)
    running_means = [sim_single[:n].mean() for n in sample_sizes]

    return {
        'mu': mu, 'sigma': sigma, 'min': min_y, 'max': max_y, 'cv': cv,
        'n_data': n_data,
        'stat_shapiro': float(stat_sw), 'p_shapiro': float(p_sw),
        'sim_single': sim_single, 'sim_total': sim_total,
        'threshold_value': threshold_value, 'target_total': target_total,
        'prob_drop': prob_drop, 'prob_below_min': prob_below_min,
        'prob_total_fail': prob_total_fail,
        'sample_sizes': sample_sizes, 'running_means': running_means,
        'yields_historis': yields,
        'df_yearly': df_yearly,
    }


# ============================================================
# JALANKAN SIMULASI
# ============================================================
if run_sim or 'mc_results' not in st.session_state:
    with st.spinner("🔄 Menjalankan simulasi Monte Carlo..."):
        results = run_monte_carlo(
            df, selected_country, selected_item,
            NIM_input, n_iterations, n_lahan, threshold_pct
        )
        if results is None:
            st.error("❌ Data tidak ditemukan untuk kombinasi negara & tanaman yang dipilih.")
            st.stop()
        st.session_state['mc_results'] = results

results = st.session_state.get('mc_results')

if results is None:
    st.info("👈 Klik tombol **🚀 Jalankan Simulasi** di sidebar untuk memulai.")
    st.stop()


# ============================================================
# TAB LAYOUT
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard Utama",
    "📈 Visualisasi",
    "🔍 Data Historis",
    "ℹ️ Tentang Aplikasi"
])


# ============================================================
# TAB 1: DASHBOARD UTAMA
# ============================================================
with tab1:
    st.markdown(f"### 📊 Hasil Simulasi Monte Carlo")
    st.markdown(f"**Studi Kasus:** {selected_country} — {selected_item}")

    # Metrik utama
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Mean (μ)", f"{results['mu']:,.0f}", "hg/ha")
    with col2:
        st.metric("Std Dev (σ)", f"{results['sigma']:,.0f}", "hg/ha")
    with col3:
        st.metric("Jumlah Data", f"{results['n_data']}", "tahun")
    with col4:
        st.metric("Koef. Variasi", f"{results['cv']:.2f}%", "")

    st.markdown("---")

    # Probabilitas risiko
    st.markdown("### ⚠️ Analisis Risiko (Probabilitas Kejadian Ekstrem)")

    col_a, col_b, col_c = st.columns(3)

    def risk_class(p):
        if p < 5: return "risk-low"
        elif p < 15: return "risk-moderate"
        else: return "risk-high"

    def risk_label(p):
        if p < 5: return "🟢 Rendah"
        elif p < 15: return "🟡 Moderat"
        else: return "🔴 Tinggi"

    with col_a:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Risiko 1: Yield Turun >{100-threshold_pct}%</h4>
            <p>Threshold: <b>{results['threshold_value']:,.0f} hg/ha</b></p>
            <h2 class="{risk_class(results['prob_drop'])}">
                {results['prob_drop']:.2f}%
            </h2>
            <p>{risk_label(results['prob_drop'])}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Risiko 2: Di Bawah Min Historis</h4>
            <p>Threshold: <b>{results['min']:,.0f} hg/ha</b></p>
            <h2 class="{risk_class(results['prob_below_min'])}">
                {results['prob_below_min']:.2f}%
            </h2>
            <p>{risk_label(results['prob_below_min'])}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_c:
        st.markdown(f"""
        <div class="metric-card">
            <h4>Risiko 3: {n_lahan} Lahan Gagal Target</h4>
            <p>Target: <b>{results['target_total']:,.0f} hg</b></p>
            <h2 class="{risk_class(results['prob_total_fail'])}">
                {results['prob_total_fail']:.2f}%
            </h2>
            <p>{risk_label(results['prob_total_fail'])}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Statistik hasil simulasi
    st.markdown("### 📋 Statistik Hasil Simulasi")
    col_x, col_y = st.columns(2)

    with col_x:
        st.markdown("#### Skenario 1 Lahan")
        sim_s = results['sim_single']
        stat_df_1 = pd.DataFrame({
            'Statistik': ['Mean', 'Median', 'Std Dev', 'P5 (Persentil 5)', 'P95 (Persentil 95)', 'Min', 'Max'],
            'Nilai (hg/ha)': [
                f"{sim_s.mean():,.2f}",
                f"{np.median(sim_s):,.2f}",
                f"{sim_s.std():,.2f}",
                f"{np.percentile(sim_s, 5):,.2f}",
                f"{np.percentile(sim_s, 95):,.2f}",
                f"{sim_s.min():,.2f}",
                f"{sim_s.max():,.2f}",
            ]
        })
        st.dataframe(stat_df_1, use_container_width=True, hide_index=True)

    with col_y:
        st.markdown(f"#### Skenario {n_lahan} Lahan (Total)")
        sim_t = results['sim_total']
        stat_df_2 = pd.DataFrame({
            'Statistik': ['Mean', 'Median', 'Std Dev', 'P5 (Persentil 5)', 'P95 (Persentil 95)', 'Min', 'Max'],
            'Nilai (hg)': [
                f"{sim_t.mean():,.2f}",
                f"{np.median(sim_t):,.2f}",
                f"{sim_t.std():,.2f}",
                f"{np.percentile(sim_t, 5):,.2f}",
                f"{np.percentile(sim_t, 95):,.2f}",
                f"{sim_t.min():,.2f}",
                f"{sim_t.max():,.2f}",
            ]
        })
        st.dataframe(stat_df_2, use_container_width=True, hide_index=True)

    # Interpretasi
    st.markdown("---")
    st.markdown("### 💡 Interpretasi Bisnis")
    st.info(f"""
    **Pertanyaan Bisnis:** Jika terdapat {n_lahan} lahan padi baru dengan kondisi iklim
    mengikuti pola historis {selected_country}, berapa probabilitas total hasil panen
    gagal memenuhi target produksi tahunan?

    **Jawaban:** Berdasarkan simulasi {n_iterations:,} iterasi dengan parameter dari data
    historis (μ={results['mu']:,.0f}, σ={results['sigma']:,.0f}), probabilitas total
    {n_lahan} lahan gagal target produksi tahunan adalah
    **{results['prob_total_fail']:.2f}%** ({risk_label(results['prob_total_fail'])}).

    **Rekomendasi Mitigasi:**
    - {"✅ Risiko agregat sangat rendah. Diversifikasi lahan efektif menurunkan risiko." if results['prob_total_fail'] < 5 else "⚠️ Risiko moderat. Pertimbangkan cadangan stok 5-10%."}
    - Siapkan strategi mitigasi (asuransi pertanian, diversifikasi varietas) untuk skenario per-lahan.
    """)


# ============================================================
# TAB 2: VISUALISASI
# ============================================================
with tab2:
    st.markdown("### 📈 Visualisasi Hasil Simulasi")

    # Plot 1: Histogram hasil + threshold
    st.markdown("#### Histogram Hasil Simulasi dengan Threshold Risiko")
    fig1, axes1 = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)

    axes1[0].hist(results['sim_single'], bins=50, color='lightblue',
                  edgecolor='black', alpha=0.7, density=True)
    axes1[0].axvline(results['threshold_value'], color='red',
                     linestyle='--', linewidth=2,
                     label=f"Threshold = {results['threshold_value']:,.0f}")
    axes1[0].axvline(results['mu'], color='green', linestyle='-', linewidth=2,
                     label=f"Mean = {results['mu']:,.0f}")
    axes1[0].axvspan(0, results['threshold_value'], alpha=0.2, color='red',
                     label=f"Area risiko ({results['prob_drop']:.2f}%)")
    axes1[0].set_title('Skenario 1 Lahan', fontsize=12, fontweight='bold')
    axes1[0].set_xlabel('Yield (hg/ha)')
    axes1[0].set_ylabel('Density')
    axes1[0].legend(loc='upper right', fontsize=9)
    axes1[0].grid(alpha=0.3)

    axes1[1].hist(results['sim_total'], bins=50, color='lightgreen',
                  edgecolor='black', alpha=0.7, density=True)
    axes1[1].axvline(results['target_total'], color='red',
                     linestyle='--', linewidth=2,
                     label=f"Target = {results['target_total']:,.0f}")
    axes1[1].axvline(results['mu'] * n_lahan, color='green',
                     linestyle='-', linewidth=2,
                     label=f"Mean = {results['mu']*n_lahan:,.0f}")
    axes1[1].axvspan(0, results['target_total'], alpha=0.2, color='red',
                     label=f"Area risiko ({results['prob_total_fail']:.2f}%)")
    axes1[1].set_title(f'Skenario {n_lahan} Lahan (Total)', fontsize=12, fontweight='bold')
    axes1[1].set_xlabel('Total Yield (hg)')
    axes1[1].set_ylabel('Density')
    axes1[1].legend(loc='upper right', fontsize=9)
    axes1[1].grid(alpha=0.3)

    st.pyplot(fig1)
    plt.close(fig1)

    st.markdown("---")

    # Plot 2: Konvergensi Monte Carlo
    st.markdown("#### Konvergensi Monte Carlo (Hukum Bilangan Besar)")
    fig2, ax2 = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax2.plot(results['sample_sizes'], results['running_means'],
             color='steelblue', linewidth=2, label='Running Mean')
    means_arr = np.array(results['running_means'])
    ax2.fill_between(results['sample_sizes'],
                     means_arr - np.std(results['sim_single']),
                     means_arr + np.std(results['sim_single']),
                     alpha=0.2, color='steelblue', label='Mean ± 1 Std')
    ax2.axhline(results['mu'], color='red', linestyle='--', linewidth=1.5,
                label=f"True Mean = {results['mu']:,.0f}")
    ax2.set_title('Konvergensi Monte Carlo: Mean Yield vs Jumlah Iterasi',
                  fontsize=12, fontweight='bold')
    ax2.set_xlabel('Jumlah Iterasi')
    ax2.set_ylabel('Mean Yield (hg/ha)')
    ax2.legend()
    ax2.grid(alpha=0.3)
    st.pyplot(fig2)
    plt.close(fig2)

    st.markdown("---")

    # Plot 3: Histogram data historis
    st.markdown("#### Histogram Data Historis")
    fig3, axes3 = plt.subplots(1, 2, figsize=(14, 4), constrained_layout=True)

    axes3[0].hist(results['yields_historis'], bins=10, color='steelblue',
                  edgecolor='black', alpha=0.7, density=True)
    axes3[0].axvline(results['mu'], color='red', linestyle='--', linewidth=2,
                     label=f'Mean = {results["mu"]:,.0f}')
    axes3[0].set_title('Histogram Yield Historis', fontsize=12, fontweight='bold')
    axes3[0].set_xlabel('Yield (hg/ha)')
    axes3[0].set_ylabel('Density')
    axes3[0].legend()
    axes3[0].grid(alpha=0.3)

    if 'Year' in results['df_yearly'].columns:
        axes3[1].plot(results['df_yearly']['Year'],
                      results['df_yearly']['hg/ha_yield'],
                      marker='o', color='darkgreen', linewidth=2, markersize=6)
        axes3[1].axhline(results['mu'], color='red', linestyle='--', alpha=0.7,
                         label=f'Mean = {results["mu"]:,.0f}')
        axes3[1].set_title('Time Series Yield Historis', fontsize=12, fontweight='bold')
        axes3[1].set_xlabel('Tahun')
        axes3[1].set_ylabel('Yield (hg/ha)')
        axes3[1].legend()
        axes3[1].grid(alpha=0.3)

    st.pyplot(fig3)
    plt.close(fig3)


# ============================================================
# TAB 3: DATA HISTORIS
# ============================================================
with tab3:
    st.markdown("### 🔍 Data Historis Yield Padi")

    st.markdown(f"**Studi Kasus:** {selected_country} — {selected_item}")
    st.markdown(f"**Jumlah tahun data:** {results['n_data']} tahun")

    st.markdown("#### Tabel Data Tahunan")
    st.dataframe(results['df_yearly'], use_container_width=True, hide_index=True)

    st.markdown("---")

    st.markdown("#### Uji Normalitas Shapiro-Wilk")
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.metric("Statistik Uji", f"{results['stat_shapiro']:.4f}")
    with col_n2:
        st.metric("p-value", f"{results['p_shapiro']:.4f}")

    if results['p_shapiro'] > 0.05:
        st.success(f"✅ p-value = {results['p_shapiro']:.4f} > 0.05 → Data BERDISTRIBUSI NORMAL. "
                  "Penggunaan np.random.normal(μ, σ) sangat tepat.")
    else:
        st.warning(f"⚠️ p-value = {results['p_shapiro']:.4f} ≤ 0.05 → Data tidak normal secara statistik. "
                  "Namun, berdasarkan Central Limit Theorem, pendekatan Normal masih valid "
                  "untuk simulasi dengan jumlah iterasi besar.")

    # Download CSV hasil
    st.markdown("---")
    st.markdown("#### 💾 Download Hasil Simulasi")
    sim_df = pd.DataFrame({
        'Iterasi': range(1, len(results['sim_single']) + 1),
        'Yield_1_Lahan': results['sim_single'],
        'Total_Yield_n_Lahan': results['sim_total'],
    })

    csv_data = sim_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Hasil Simulasi (CSV)",
        data=csv_data,
        file_name=f'hasil_simulasi_monte_carlo_{selected_country}_{selected_item}.csv',
        mime='text/csv',
    )


# ============================================================
# TAB 4: TENTANG APLIKASI
# ============================================================
with tab4:
    st.markdown("### ℹ️ Tentang Aplikasi")

    st.markdown("""
    #### 📋 Deskripsi
    Aplikasi web ini adalah implementasi dari **Tugas Akhir 03 (TA-03)**
    mata kuliah **Praktikum Pemodelan dan Simulasi**.

    Aplikasi melakukan **Simulasi Monte Carlo** untuk mengestimasi
    probabilitas risiko kegagalan panen (yield) padi di Indonesia
    berdasarkan data historis dari Kaggle.

    #### 🎯 Tujuan
    1. Mengidentifikasi distribusi data riil dari dataset Kaggle.
    2. Membangun model simulasi Monte Carlo berdasarkan data historis.
    3. Melakukan Analisis Risiko (Risk Assessment) dengan probabilitas kejadian ekstrem.

    #### 🛠️ Teknologi
    - **Streamlit** - Web framework untuk data science
    - **NumPy** - Komputasi numerik & random number generator
    - **Pandas** - Manipulasi data
    - **Matplotlib** - Visualisasi
    - **SciPy** - Uji statistik (Shapiro-Wilk)

    #### 📊 Cara Menggunakan
    1. Atur parameter simulasi di sidebar kiri (NIM, jumlah iterasi, jumlah lahan, threshold).
    2. Klik tombol **🚀 Jalankan Simulasi**.
    3. Lihat hasil di tab **Dashboard Utama**, **Visualisasi**, dan **Data Historis**.
    4. Download hasil simulasi dalam format CSV.

    #### 👨‍💻 Author
    **Atsaal Najwan** (NIM: 301240012)
    - Mata Kuliah: Praktikum Pemodelan dan Simulasi
    - Dosen Pengampu: Mohammad Bayu Anggara, S.Kom., M.Kom.
    - Tahun: 2026

    #### 📚 Referensi
    - Modul Praktikum Pemodelan dan Simulasi - Modul 3 (Metode Monte Carlo)
    - Law, A. M. (2015). Simulation Modeling and Analysis (5th ed.). McGraw-Hill.
    - Raychaudhuri, S. (2008). Introduction to Monte Carlo simulation. WSC 2008.
    - Dataset: Kaggle - Crop Yield Prediction Dataset (yield_df.csv)
    """)

    st.markdown("---")
    st.markdown("*Aplikasi ini dibuat untuk tujuan edukasi sebagai bagian dari TA-03.*")
