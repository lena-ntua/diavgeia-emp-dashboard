"""
Παρατηρητήριο Αποφάσεων και Δαπανών ΕΜΠ
Dashboard με δεδομένα της Διαύγειας (dataset glossAPI/diavgeia).
"""

import time
import unicodedata

import pandas as pd
import plotly.express as px
import requests
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


def xoris_tonous(keimeno):
    """Αφαιρεί τόνους/διαλυτικά και κάνει κεφαλαία, ώστε η αναζήτηση
    να βρίσκει π.χ. το «καθαριότητα» όταν ο χρήστης γράφει «ΚΑΘΑΡΙΟΤΗΤΑ»."""
    keimeno = unicodedata.normalize("NFD", str(keimeno))
    keimeno = "".join(c for c in keimeno if unicodedata.category(c) != "Mn")
    return keimeno.upper()


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
    df["thema_anazitisi"] = df["thema"].fillna("").map(xoris_tonous)
    return df


@st.cache_data
def keimena():
    """Τα κείμενα των αναθέσεων/συμβάσεων, για τις περιλήψεις."""
    k = pd.read_parquet("emp_keimena.parquet")
    return dict(zip(k["ada"], k["keimeno"]))


ODIGIES_LLM = """Είσαι βοηθός που εξηγεί αποφάσεις της ελληνικής δημόσιας διοίκησης σε απλούς πολίτες.
Διάβασε την παρακάτω απόφαση του Εθνικού Μετσόβιου Πολυτεχνείου από τη Διαύγεια και γράψε
περίληψη 3-4 προτάσεων σε απλά, καθημερινά ελληνικά, χωρίς νομικούς όρους. Πες:
- τι αποφασίστηκε,
- ποιος πληρώνεται (ανάδοχος),
- πόσα χρήματα,
- για ποιο σκοπό.
Χρησιμοποίησε ΜΟΝΟ πληροφορίες που υπάρχουν στο κείμενο. Αν κάτι δεν αναφέρεται, γράψε ότι δεν αναφέρεται.
Μην προσθέτεις εισαγωγή ή επίλογο.

ΘΕΜΑ: {thema}

ΚΕΙΜΕΝΟ ΑΠΟΦΑΣΗΣ:
{keimeno}"""


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 7)
def perilipsi(ada, thema, keimeno):
    """Στέλνει την απόφαση στο Google Gemini και επιστρέφει περίληψη.
    Κρατά τις απαντήσεις μία εβδομάδα, για να μην ξοδεύεται το δωρεάν όριο."""
    kleidi = st.secrets["GEMINI_API_KEY"]
    # Πρώτα το βασικό μοντέλο· αν είναι φορτωμένο, εναλλακτικά μοντέλα Flash
    montela = [st.secrets.get("GEMINI_MODEL", "gemini-3.8-flash"), "gemini-flash-latest", "gemini-flash-lite-latest"]
    keimeno_prompt = ODIGIES_LLM.format(thema=thema, keimeno=keimeno)
    teleftaio_lathos = "άγνωστο σφάλμα"

    for montelo in montela:
        for prospatheia in range(2):  # 2 προσπάθειες ανά μοντέλο
            try:
                apantisi = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{montelo}:generateContent",
                    headers={"x-goog-api-key": kleidi},
                    json={"contents": [{"parts": [{"text": keimeno_prompt}]}]},
                    timeout=90,
                )
            except requests.RequestException:
                teleftaio_lathos = "δεν υπήρξε σύνδεση με το Gemini"
                time.sleep(2)
                continue
            if apantisi.status_code == 200:
                meri = apantisi.json()["candidates"][0]["content"]["parts"]
                return "".join(m.get("text", "") for m in meri if not m.get("thought")).strip()
            if apantisi.status_code in (400, 401, 403):
                raise RuntimeError("Το κλειδί του Gemini δεν έγινε δεκτό. Ελέγξτε τα Secrets της εφαρμογής.")
            if apantisi.status_code == 404:
                break  # το μοντέλο δεν υπάρχει → επόμενο μοντέλο
            # 429 (όριο) ή 5xx (φορτωμένος server): περιμένουμε λίγο και ξαναδοκιμάζουμε
            teleftaio_lathos = f"κωδικός {apantisi.status_code}"
            time.sleep(3 * (prospatheia + 1))

    raise RuntimeError(
        f"Η υπηρεσία Gemini είναι προσωρινά φορτωμένη ({teleftaio_lathos}). Δοκιμάστε ξανά σε λίγα λεπτά."
    )


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
    fd = fd[fd["thema_anazitisi"].str.contains(xoris_tonous(lexi), regex=False)]

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

# ---------------- Περίληψη με LLM ----------------
st.subheader("🤖 Περίληψη απόφασης σε απλή γλώσσα")

try:
    exei_kleidi = "GEMINI_API_KEY" in st.secrets
except Exception:  # δεν υπάρχει καθόλου αρχείο secrets
    exei_kleidi = False

if not exei_kleidi:
    st.info("Οι περιλήψεις δεν είναι διαθέσιμες: δεν έχει οριστεί κλειδί για το Google Gemini.")
else:
    kei = keimena()
    diathesimes = anatheseis[anatheseis["ada"].isin(kei.keys())].sort_values("poso", ascending=False).head(500)
    if diathesimes.empty:
        st.write("Δεν υπάρχουν αναθέσεις με κείμενο για τα φίλτρα που επιλέξατε.")
    else:
        etiketes = {
            r.ada: f"{r.imerominia:%d/%m/%Y} · {euro(r.poso)} · {str(r.thema)[:90]}"
            for r in diathesimes.itertuples()
        }
        ada = st.selectbox(
            "Επιλέξτε απόφαση (οι 500 μεγαλύτερες αναθέσεις με βάση τα φίλτρα — μπορείτε και να πληκτρολογήσετε):",
            list(etiketes),
            format_func=etiketes.get,
        )
        epilogi = diathesimes[diathesimes["ada"] == ada].iloc[0]
        st.markdown(
            f"**Ανάδοχος:** {epilogi['anadoxos'] or '—'} · **Ποσό:** {euro(epilogi['poso'])} · "
            f"[Η απόφαση στη Διαύγεια]({epilogi['link']})"
        )
        if st.button("✨ Φτιάξε περίληψη", type="primary"):
            with st.spinner("Το Gemini διαβάζει την απόφαση..."):
                try:
                    st.success(perilipsi(ada, epilogi["thema"], kei[ada]))
                    st.caption(
                        "⚠️ Η περίληψη δημιουργήθηκε αυτόματα από τεχνητή νοημοσύνη (Google Gemini) "
                        "και μπορεί να περιέχει λάθη. Ελέγξτε πάντα την πρωτότυπη απόφαση."
                    )
                except Exception as e:
                    st.error(f"Δεν ήταν δυνατή η περίληψη: {e}")
