"""
Παρατηρητήριο Αποφάσεων και Δαπανών ΕΜΠ
Dashboard με δεδομένα της Διαύγειας (dataset glossAPI/diavgeia).
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Παρατηρητήριο Δαπανών ΕΜΠ",
    page_icon="🏛️",
    layout="wide",
)

# Ονομασίες τύπων αποφάσεων της Διαύγειας
TYPOI = {
    "Β.2.1": "Ανάθεση / Κατακύρωση",
    "Β.2.2": "Ανάληψη Υποχρέωσης",
    "Β.1.1": "Διορισμός / Πρόσληψη",
    "Β.1.2": "Λύση Υπαλληλικής Σχέσης",
    "Β.1.3": "Μεταβολή Ανθρώπινου Δυναμικού",
    "Γ.3.4": "Λοιπές ατομικές πράξεις",
    "2.4.7.1": "Λοιπές ατομικές διοικητικές πράξεις",
    "2.4.6.1": "Πράξεις Συλλογικών Οργάνων",
    "Α.2": "Κανονιστική Πράξη",
    "Δ.1": "Σύμβαση",
    "Δ.2.1": "Δαπάνη / Περίληψη Διακήρυξης",
    "Δ.2.2": "Εντολή Πληρωμής / Κατακύρωση",
    "Γ.2": "Οικονομικές πράξεις",
    "Γ.3.1": "Λοιπές πράξεις (Γ.3.1)",
    "Γ.3.3": "Λοιπές πράξεις (Γ.3.3)",
    "100": "Χωρίς κατηγορία",
}


def euro(x):
    """Μορφή ποσού στα ελληνικά, π.χ. 1.234.567 €"""
    return f"{x:,.0f} €".replace(",", ".")


@st.cache_data
def fortosi():
    df = pd.read_parquet("emp_apofaseis.parquet")
    df["imerominia"] = pd.to_datetime(df["imerominia"])
    df["perigrafi_typou"] = df["typos"].map(TYPOI).fillna(df["typos"])
    df["minas"] = df["imerominia"].dt.to_period("M").dt.to_timestamp()
    df["link"] = "https://diavgeia.gov.gr/doc/" + df["ada"]
    return df


df = fortosi()

# ---------------- Επικεφαλίδα ----------------
st.title("🏛️ Παρατηρητήριο Αποφάσεων και Δαπανών ΕΜΠ")
st.caption(
    "Αποφάσεις του Εθνικού Μετσόβιου Πολυτεχνείου στη Διαύγεια, 2022–2026. "
    "Πηγή: dataset glossAPI/diavgeia (CC BY 4.0)."
)

# ---------------- Φίλτρα (αριστερή στήλη) ----------------
st.sidebar.header("🔎 Φίλτρα")

elaxisti, megisti = df["imerominia"].min().date(), df["imerominia"].max().date()
periodos = st.sidebar.date_input(
    "Χρονική περίοδος",
    value=(elaxisti, megisti),
    min_value=elaxisti,
    max_value=megisti,
    format="DD/MM/YYYY",
)
if isinstance(periodos, tuple) and len(periodos) == 2:
    apo, eos = periodos
else:
    apo, eos = elaxisti, megisti

monades = ["Όλες"] + sorted(df["monada"].dropna().unique().tolist())
monada = st.sidebar.selectbox("Υπηρεσία του ΕΜΠ", monades)

lexi = st.sidebar.text_input("Αναζήτηση στο θέμα", placeholder="π.χ. προμήθεια, καθαριότητα")

# Εφαρμογή φίλτρων
fd = df[(df["imerominia"].dt.date >= apo) & (df["imerominia"].dt.date <= eos)]
if monada != "Όλες":
    fd = fd[fd["monada"] == monada]
if lexi:
    fd = fd[fd["thema"].fillna("").str.contains(lexi, case=False, regex=False)]

anatheseis = fd[(fd["typos"] == "Β.2.1") & fd["poso"].notna()]

# ---------------- Βασικοί αριθμοί ----------------
k1, k2, k3 = st.columns(3)
k1.metric("Αποφάσεις", f"{len(fd):,}".replace(",", "."))
k2.metric("Αναθέσεις (δαπάνες)", f"{len(anatheseis):,}".replace(",", "."))
k3.metric("Συνολικό ποσό αναθέσεων", euro(anatheseis["poso"].sum()))

st.info(
    "ℹ️ **Πώς μετράμε τις δαπάνες:** χρησιμοποιούμε μόνο τις αποφάσεις τύπου "
    "*Ανάθεση / Κατακύρωση (Β.2.1)*, για να μη μετρηθεί δύο φορές η ίδια δαπάνη "
    "(η ίδια δαπάνη εμφανίζεται συχνά και ως «Ανάληψη Υποχρέωσης»).  \n"
    "⚠️ **Κενά στα δεδομένα:** το dataset δεν περιέχει όλους τους μήνες "
    "(π.χ. λείπουν οι πρώτοι μήνες του 2025 και μεγάλο μέρος του 2026). "
    "Μήνες με πολύ χαμηλές τιμές οφείλονται συνήθως σε αυτό και όχι σε πραγματική μείωση."
)

# ---------------- Γραφήματα ----------------
st.subheader("📈 Δαπάνες ανά μήνα")
ana_mina = anatheseis.groupby("minas", as_index=False)["poso"].sum()
gr1 = px.bar(
    ana_mina, x="minas", y="poso",
    labels={"minas": "Μήνας", "poso": "Ποσό (€)"},
)
gr1.update_traces(hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} €<extra></extra>")
st.plotly_chart(gr1, width="stretch")

aristera, dexia = st.columns(2)

with aristera:
    st.subheader("🏆 Οι 10 μεγαλύτεροι ανάδοχοι")
    top10 = (
        anatheseis.dropna(subset=["anadoxos"])
        .groupby("anadoxos", as_index=False)["poso"].sum()
        .nlargest(10, "poso")
        .sort_values("poso")
    )
    gr2 = px.bar(
        top10, x="poso", y="anadoxos", orientation="h",
        labels={"poso": "Ποσό (€)", "anadoxos": ""},
    )
    gr2.update_traces(hovertemplate="%{y}<br>%{x:,.0f} €<extra></extra>")
    st.plotly_chart(gr2, width="stretch")

with dexia:
    st.subheader("🗂️ Αποφάσεις ανά τύπο")
    ana_typo = fd["perigrafi_typou"].value_counts().head(10).sort_values().reset_index()
    ana_typo.columns = ["typos", "plithos"]
    gr3 = px.bar(
        ana_typo, x="plithos", y="typos", orientation="h",
        labels={"plithos": "Πλήθος αποφάσεων", "typos": ""},
    )
    st.plotly_chart(gr3, width="stretch")

# ---------------- Πίνακας αναθέσεων ----------------
st.subheader("📋 Οι αναθέσεις αναλυτικά")
st.caption("Ταξινομημένες από τη μεγαλύτερη. Πατήστε «Άνοιγμα» για να δείτε την απόφαση στη Διαύγεια.")

pinakas = anatheseis.sort_values("poso", ascending=False)[
    ["imerominia", "thema", "anadoxos", "poso", "monada", "link"]
]
st.dataframe(
    pinakas,
    hide_index=True,
    width="stretch",
    column_config={
        "imerominia": st.column_config.DateColumn("Ημερομηνία", format="DD/MM/YYYY"),
        "thema": st.column_config.TextColumn("Θέμα", width="large"),
        "anadoxos": "Ανάδοχος",
        "poso": st.column_config.NumberColumn("Ποσό (€)", format="%.2f €"),
        "monada": "Υπηρεσία",
        "link": st.column_config.LinkColumn("Διαύγεια", display_text="Άνοιγμα"),
    },
)

st.download_button(
    "⬇️ Λήψη των αναθέσεων σε CSV",
    pinakas.to_csv(index=False).encode("utf-8-sig"),
    file_name="anatheseis_emp.csv",
    mime="text/csv",
)
