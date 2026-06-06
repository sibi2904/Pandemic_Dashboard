import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Data Loading ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading dataset…")
def load_data():
    cols = ['iso_code', 'continent', 'location', 'date',
            'total_cases', 'total_deaths', 'total_vaccinations',
            'new_cases_smoothed', 'population']
    df = pd.read_csv('data/corona_dataset.csv', usecols=cols)
    # Drop OWID aggregate rows (World, Asia, Europe…) — continent is NaN for them
    df = df[df['continent'].notna()].copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['location', 'date'])
    # Forward-fill cumulative columns within each country to close gaps
    for col in ['total_cases', 'total_deaths', 'total_vaccinations']:
        df[col] = df.groupby('location')[col].ffill().fillna(0)
    df['new_cases_smoothed'] = df['new_cases_smoothed'].fillna(0)
    return df

df_raw = load_data()

# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt(n, suffix=''):
    """Format large numbers compactly: 1.23B / 456.7M / 12.3k"""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B{suffix}"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M{suffix}"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}k{suffix}"
    return f"{n:,.0f}{suffix}"

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global Pandemic Intelligence Center",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body {
        overflow: hidden !important;
        height: 100vh !important;
        max-height: 100vh !important;
        background-color: #000000 !important;
        color: #FFFFFF;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }

    /* Space Nebula background */
    .stApp {
        background: radial-gradient(circle at 15% 50%, rgba(132,255,0,0.15), transparent 50%), radial-gradient(circle at 85% 30%, rgba(57,255,182,0.1), transparent 50%), url('https://www.transparenttextures.com/patterns/stardust.png'), #000000 !important;
        overflow: hidden !important;
        height: 100vh !important;
        max-height: 100vh !important;
    }

    /* Lock stApp inner layers */
    .stApp > div,
    section.main,
    section.main > div,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stAppViewBlockContainer"] {
        background: transparent !important;
        overflow: hidden !important;
        height: 100vh !important;
        max-height: 100vh !important;
    }

    /* Hide header/footer */
    header[data-testid="stHeader"], header { visibility: hidden !important; height: 0 !important; }
    footer { visibility: hidden !important; height: 0 !important; }

    /* Make block-container look like the browser window */
    .block-container {
        background: #020202 !important; /* Deep obsidian black */
        border: 2px solid #84FF00 !important;
        border-radius: 12px !important;
        box-shadow: 0 0 40px rgba(132,255,0,0.5), inset 0 0 20px rgba(132,255,0,0.1) !important;
        margin-top: 1vh !important;
        margin-bottom: 1vh !important;
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 95% !important;
        height: 98vh !important;
        max-height: 98vh !important;
        overflow: hidden !important;
        position: relative;
    }

    /* Removed Browser window controls pseudo-element */

    .block-container > div:first-child, .block-container > div:first-child > div:first-child { margin-top: 0 !important; padding-top: 0 !important; }
    div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none !important; }

    /* Title */
    .dashboard-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 700;
        color: #84FF00;
        margin-top: -15px !important;
        margin-bottom: 1rem;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        border-bottom: none;
        padding-bottom: 0px;
        text-shadow: 0 0 15px rgba(132,255,0,0.5);
    }
    .title-icon { display: flex; align-items: center; justify-content: center; filter: drop-shadow(0 0 10px rgba(132,255,0,0.6)); }

    /* KPI Cards */
    .glass-kpi {
        background: #000000;
        border: 1px solid rgba(132,255,0,0.6);
        border-radius: 4px;
        padding: 0.6rem 0.2rem;
        height: 75px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }
    .kpi-top { margin-bottom: 0.2rem; }
    .kpi-label { font-size: 12px; color: #FFFFFF; font-weight: 400; }
    .kpi-val { font-size: 2.2rem; color: #84FF00; font-weight: 600; line-height: 1.0; text-shadow: 0 0 10px rgba(132,255,0,0.5); }

    /* Chart Containers */
    div[data-testid="stPlotlyChart"] {
        background: #000000;
        border: 1px solid rgba(132,255,0,0.6);
        border-radius: 4px;
        padding: 0.2rem;
    }

    /* Filter Dropdowns */
    div[data-baseweb="select"] > div {
        background-color: #000000 !important;
        border: 1px solid rgba(132,255,0,0.6) !important;
        border-radius: 4px !important;
        color: #84FF00 !important;
    }
    .stSelectbox label p { color: #FFFFFF !important; }
    div[data-testid="column"] { padding: 0 0.2rem; }
</style>
""", unsafe_allow_html=True)

# ── Filter State Helpers ───────────────────────────────────────────────────────
continents_list = ['All Continents'] + sorted(df_raw['continent'].unique().tolist())
years_list      = ['All Years'] + [str(y) for y in sorted(df_raw['date'].dt.year.unique())]

sel_continent = st.session_state.get('sel_continent', 'All Continents')

if sel_continent != 'All Continents':
    country_opts = ['All Countries'] + sorted(
        df_raw[df_raw['continent'] == sel_continent]['location'].unique().tolist())
else:
    country_opts = ['All Countries'] + sorted(df_raw['location'].unique().tolist())

sel_country = st.session_state.get('sel_country', 'All Countries')
sel_year    = st.session_state.get('sel_year',    'All Years')

# ── Apply Filters ──────────────────────────────────────────────────────────────
df_filtered = df_raw.copy()
if sel_continent != 'All Continents':
    df_filtered = df_filtered[df_filtered['continent'] == sel_continent]
if sel_country != 'All Countries':
    df_filtered = df_filtered[df_filtered['location'] == sel_country]
if sel_year != 'All Years':
    df_filtered = df_filtered[df_filtered['date'].dt.year == int(sel_year)]

# ── KPI Aggregation ────────────────────────────────────────────────────────────
if not df_filtered.empty:
    latest = df_filtered.sort_values('date').groupby('location').last().reset_index()
    total_cases    = float(latest['total_cases'].sum())
    total_deaths   = float(latest['total_deaths'].sum())
    total_vax      = float(latest['total_vaccinations'].sum())
    total_recovered = max(total_cases - total_deaths, 0.0)
    mortality      = (total_deaths   / total_cases * 100) if total_cases > 0 else 0.0
    recovery_rate  = (total_recovered / total_cases * 100) if total_cases > 0 else 0.0
else:
    latest = pd.DataFrame()
    total_cases = total_deaths = total_vax = mortality = recovery_rate = 0.0

# ─────────────────────────────────────────────────────────────────────────────
# 1. TITLE
# ─────────────────────────────────────────────────────────────────────────────
svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#84FF00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>'
st.markdown(f'<div class="dashboard-title"><span class="title-icon">{svg_icon}</span> Global Pandemic Intelligence Center</div>',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 2. KPI CARDS  (5 equal-width columns)
# ─────────────────────────────────────────────────────────────────────────────
kpi_cols = st.columns(5)

with kpi_cols[0]:
    st.markdown(f'''
    <div class="glass-kpi">
        <div class="kpi-top"><span class="kpi-label">Total Cases</span></div>
        <div class="kpi-val">{fmt(total_cases)}</div>
    </div>
    ''', unsafe_allow_html=True)

with kpi_cols[1]:
    st.markdown(f'''
    <div class="glass-kpi">
        <div class="kpi-top"><span class="kpi-label">Total Deaths</span></div>
        <div class="kpi-val">{fmt(total_deaths)}</div>
    </div>
    ''', unsafe_allow_html=True)

with kpi_cols[2]:
    st.markdown(f'''
    <div class="glass-kpi">
        <div class="kpi-top"><span class="kpi-label">Vaccinations</span></div>
        <div class="kpi-val">{fmt(total_vax)}</div>
    </div>
    ''', unsafe_allow_html=True)

with kpi_cols[3]:
    st.markdown(f'''
    <div class="glass-kpi">
        <div class="kpi-top"><span class="kpi-label">Mortality Rate</span></div>
        <div class="kpi-val">{mortality:.2f}%</div>
    </div>
    ''', unsafe_allow_html=True)

with kpi_cols[4]:
    st.markdown(f'''
    <div class="glass-kpi">
        <div class="kpi-top"><span class="kpi-label">Recovery Rate</span></div>
        <div class="kpi-val">{recovery_rate:.2f}%</div>
    </div>
    ''', unsafe_allow_html=True)

st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3. FILTER ROW  (3 centered equal-width dropdowns, own dedicated row)
# ─────────────────────────────────────────────────────────────────────────────
_, fcol1, fcol2, fcol3, _ = st.columns([0.5, 1, 1, 1, 0.5])

with fcol1:
    st.selectbox('🌎 Continent', continents_list, key='sel_continent')

with fcol2:
    # Reflect current continent selection immediately
    cur_continent = st.session_state.get('sel_continent', 'All Continents')
    if cur_continent != 'All Continents':
        country_opts_cur = ['All Countries'] + sorted(
            df_raw[df_raw['continent'] == cur_continent]['location'].unique().tolist())
    else:
        country_opts_cur = ['All Countries'] + sorted(df_raw['location'].unique().tolist())
    # Guard stale country
    if st.session_state.get('sel_country', 'All Countries') not in country_opts_cur:
        st.session_state['sel_country'] = 'All Countries'
    st.selectbox('📍 Location / Country', country_opts_cur, key='sel_country')

with fcol3:
    st.selectbox('📅 Year', years_list, key='sel_year')

st.markdown("<div style='height:0.15rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 4. CHART ROW 1  — Line | Horizontal Bar | Treemap
# ─────────────────────────────────────────────────────────────────────────────
bg_color   = 'rgba(0,0,0,0)'
font_color = '#FFFFFF'
grid_color = 'rgba(132,255,0,0.1)'

c1_cols = st.columns(3)

# ── Chart 1: Global Cases Trend (Line) ────────────────────────────────────────
with c1_cols[0]:
    if not df_filtered.empty:
        df_line = df_filtered.groupby('date')['total_cases'].sum().reset_index()
    else:
        df_line = pd.DataFrame({
            'date': pd.Series(dtype='datetime64[ns]'),
            'total_cases': pd.Series(dtype='float')
        })

    fig1 = px.line(df_line, x='date', y='total_cases',
                   title='Pandemic Case Evolution Over Time', render_mode='svg')
    fig1.update_layout(
        plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=font_color,
        title_font=dict(size=11, color='#FFFFFF', family='Inter'),
        margin=dict(l=5, r=5, t=30, b=5), height=190,
        xaxis=dict(showgrid=False, title='', showline=False, tickfont=dict(size=9, color='#FFFFFF')),
        yaxis=dict(showgrid=True, gridcolor=grid_color, title='', tickfont=dict(size=9, color='#FFFFFF')),
        hoverlabel=dict(bgcolor='#000000', bordercolor='#84FF00', font=dict(color='white'))
    )
    fig1.update_yaxes(tickformat='.2s')
    fig1.update_traces(
        line_color='#84FF00', line_width=2.5, line_shape='spline',
        fill='tozeroy', fillcolor='rgba(132,255,0,0.1)',
        hovertemplate='Date: %{x|%b %Y}<br>Cases: %{y:,.2s}<extra></extra>'
    )
    st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

# ── Chart 2: Top 7 Affected Countries (Horizontal Bar) ────────────────────────
with c1_cols[1]:
    if not latest.empty:
        df_bar = (latest.nlargest(7, 'total_cases')
                        .sort_values('total_cases', ascending=True)
                        .copy())
        df_bar['label'] = df_bar['total_cases'].apply(fmt)
    else:
        df_bar    = pd.DataFrame({'location': [], 'total_cases': [], 'label': []})

    fig2 = px.bar(
        df_bar, x='total_cases', y='location', orientation='h',
        title='Highest Impacted Countries',
        text='label' if not df_bar.empty else None
    )
    fig2.update_layout(
        plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=font_color,
        title_font=dict(size=11, color='#FFFFFF', family='Inter'),
        margin=dict(l=5, r=40, t=30, b=5), height=190,
        xaxis=dict(showgrid=False, showticklabels=False, title=''),
        yaxis=dict(showgrid=False, title='', tickfont=dict(size=9, color='#FFFFFF')),
        hoverlabel=dict(bgcolor='#000000', bordercolor='#84FF00', font=dict(color='white'))
    )
    fig2.update_traces(
        marker_color='#84FF00',
        textposition='outside',
        textfont=dict(size=9, color='#FFFFFF'),
        cliponaxis=False,
        hovertemplate='<b>%{y}</b><br>Cases: %{text}<extra></extra>'
    )
    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

# ── Chart 3: Continent-wise Case Distribution (Treemap) ───────────────────────
with c1_cols[2]:
    if not df_filtered.empty:
        df_tree = (
            df_filtered[df_filtered['continent'].notna()]
            .groupby(['continent', 'location'], as_index=False)['total_cases'].max()
            .groupby('continent', as_index=False)['total_cases'].sum()
        )
        df_tree = df_tree[df_tree['total_cases'] > 0].reset_index(drop=True)
        total_global_cases = df_tree['total_cases'].sum()
        df_tree['pct'] = (df_tree['total_cases'] / total_global_cases * 100).round(2) if total_global_cases > 0 else 0.0
        df_tree['label_fmt'] = df_tree['total_cases'].apply(fmt)
    else:
        df_tree = pd.DataFrame({'continent': [], 'total_cases': [], 'pct': [], 'label_fmt': []})
        total_global_cases = 0.0

    fig3 = go.Figure(go.Treemap(
        labels=df_tree['continent'].tolist() if not df_tree.empty else [],
        parents=['' ] * len(df_tree),
        values=df_tree['total_cases'].tolist() if not df_tree.empty else [],
        customdata=list(zip(
            df_tree['label_fmt'].tolist(),
            df_tree['pct'].tolist()
        )) if not df_tree.empty else [],
        texttemplate='<b>%{label}</b><br>%{customdata[0]}',
        hovertemplate=(
            '<b>%{label}</b><br>'
            'Cases: %{customdata[0]}<br>'
            'Share: %{customdata[1]:.2f}%'
            '<extra></extra>'
        ),
        marker=dict(
            colorscale=[[0, '#1a3300'], [1, '#84FF00']],
            line=dict(color='#84FF00', width=1),
        ),
        textfont=dict(size=10, color='#FFFFFF', family='Inter'),
        tiling=dict(pad=2),
    ))
    fig3.update_layout(
        plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=font_color,
        title='Pandemic Impact by Continent',
        title_font=dict(size=11, color='#FFFFFF', family='Inter'),
        margin=dict(l=5, r=5, t=30, b=15), height=170,
        hoverlabel=dict(bgcolor='#000000', bordercolor='#84FF00', font=dict(color='white'))
    )
    st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})

st.markdown("<div style='height:0.2rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 5. CHART ROW 2  — Horizontal Grouped Bar | Pie | Vertical Column Chart
# ─────────────────────────────────────────────────────────────────────────────
c2_cols = st.columns(3)

# ── Chart 4: Choropleth Map – Cases by Country ────────────────────────────────
with c2_cols[0]:
    if not latest.empty:
        df_map = latest[latest['total_cases'] > 0][['location', 'iso_code', 'total_cases']].copy()
        df_map['cases_fmt'] = df_map['total_cases'].apply(fmt)
    else:
        df_map = pd.DataFrame({'location': [], 'iso_code': [], 'total_cases': [], 'cases_fmt': []})

    fig4 = go.Figure(go.Choropleth(
        locations=df_map['iso_code'].tolist(),
        z=df_map['total_cases'].tolist(),
        text=df_map['location'].tolist(),
        customdata=df_map['cases_fmt'].tolist(),
        colorscale=[[0, '#001a00'], [0.3, '#1a4d00'], [0.6, '#4d9900'], [1, '#84FF00']],
        showscale=False,
        marker_line_color='#84FF00',
        marker_line_width=0.3,
        hovertemplate='<b>%{text}</b><br>Cases: %{customdata}<extra></extra>',
    ))
    fig4.update_layout(
        plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=font_color,
        title='Geographic Spread of Cases',
        title_font=dict(size=11, color='#FFFFFF', family='Inter'),
        margin=dict(l=0, r=0, t=25, b=15), height=170,
        showlegend=False,
        geo=dict(
            bgcolor='#000000',
            showframe=False,
            showcoastlines=True,
            coastlinecolor='rgba(132,255,0,0.3)',
            showland=True, landcolor='#0d1a00',
            showocean=True, oceancolor='#000000',
            showcountries=True, countrycolor='rgba(132,255,0,0.2)',
            projection_type='equirectangular',
            lataxis_range=[-60, 85],
            lonaxis_range=[-180, 180],
            domain=dict(x=[0, 1], y=[0.05, 1]),
        ),
        hoverlabel=dict(bgcolor='#000000', bordercolor='#84FF00', font=dict(color='white'))
    )
    st.plotly_chart(fig4, use_container_width=True, config={'displayModeBar': False})

# ── Chart 5: Global Vaccination Coverage (Doughnut) ───────────────────────────
with c2_cols[1]:
    if not latest.empty and 'population' in latest.columns:
        df_vax_calc = latest[latest['population'] > 0].copy()
        df_vax_calc['vax_people'] = (df_vax_calc['total_vaccinations'] / 2).clip(upper=df_vax_calc['population'])
        vaccinated_est = float(df_vax_calc['vax_people'].sum())
        total_pop      = float(df_vax_calc['population'].sum())
        vax_pct  = min((vaccinated_est / total_pop * 100), 100) if total_pop > 0 else 72.0
    else:
        vax_pct   = 72.0

    unvax_pct = max(100.0 - vax_pct, 0.0)
    df_pie5   = pd.DataFrame({
        'Category':   ['Vaccinated', 'Not Vaccinated'],
        'Value':      [round(vax_pct, 1), round(unvax_pct, 1)],
    })

    fig5 = px.pie(
        df_pie5, values='Value', names='Category',
        title='Vaccinated vs Unvaccinated Population',
        color='Category',
        color_discrete_map={'Vaccinated': '#84FF00', 'Not Vaccinated':  '#1a3300'}
    )
    fig5.update_traces(
        hole=0.65,
        textposition='outside',
        textinfo='label+percent',
        textfont=dict(size=9, color='#FFFFFF', family='Inter'),
        marker=dict(line=dict(color='#000000', width=2)),
        pull=[0.03, 0.03],
        hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>',
    )
    fig5.update_layout(
        plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=font_color,
        title_font=dict(size=11, color='#FFFFFF', family='Inter'),
        margin=dict(l=20, r=20, t=30, b=15), height=170,
        showlegend=False,
        annotations=[dict(text=f"{vax_pct:.1f}%", x=0.5, y=0.5, font_size=16, font_color='#84FF00', showarrow=False)],
        hoverlabel=dict(bgcolor='#000000', bordercolor='#84FF00', font=dict(color='white'))
    )
    st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})

# ── Chart 6: Top 7 Countries by Total Deaths (Vertical Column Chart) ──────────
with c2_cols[2]:
    if not df_filtered.empty:
        df_top7 = (
            df_filtered[df_filtered['location'].notna()]
            .groupby('location', as_index=False)['total_deaths'].max()
        )
        df_top7 = (df_top7.nlargest(7, 'total_deaths')
                          .sort_values('total_deaths', ascending=False)
                          .reset_index(drop=True))
        df_top7['label_fmt'] = df_top7['total_deaths'].apply(fmt)
    else:
        df_top7 = pd.DataFrame({'location': [], 'total_deaths': [], 'label_fmt': []})

    fig6 = go.Figure(go.Bar(
        x=df_top7['location'].tolist(),
        y=df_top7['total_deaths'].tolist(),
        marker=dict(color='#84FF00', line=dict(width=0)),
        text=df_top7['label_fmt'].tolist() if not df_top7.empty else [],
        textposition='outside',
        textfont=dict(size=9, color='#FFFFFF'),
        cliponaxis=False,
        hovertemplate='<b>%{x}</b><br>Deaths: %{text}<extra></extra>',
        hoverlabel=dict(bgcolor='#000000', bordercolor='#84FF00', font=dict(color='white'))
    ))

    fig6.update_layout(
        plot_bgcolor=bg_color, paper_bgcolor=bg_color, font_color=font_color,
        title='Death Burden by Country',
        title_font=dict(size=11, color='#FFFFFF', family='Inter'),
        margin=dict(l=5, r=5, t=30, b=15), height=170,
        showlegend=False,
        xaxis=dict(showgrid=False, title='', tickfont=dict(size=9, color='#FFFFFF'), tickangle=-20),
        yaxis=dict(showgrid=True, gridcolor=grid_color, title='', tickfont=dict(size=8, color='#FFFFFF'), tickformat='.2s'),
        bargap=0.3
    )
    st.plotly_chart(fig6, use_container_width=True, config={'displayModeBar': False})