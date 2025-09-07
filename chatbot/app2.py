import mysql.connector
from openai import OpenAI
import pandas as pd
import streamlit as st
from datetime import datetime
# -*- coding: utf-8 -*-

# -----------------------------
# Configuration OpenAI
# -----------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Assistant SQL",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# CSS custom pour style "chat"
# -----------------------------
st.markdown("""
<style>
.chat-bubble-user {
    background: #0078ff;
    color: white;
    padding: 0.8rem 1rem;
    border-radius: 15px 15px 0 15px;
    max-width: 70%;
    margin: 5px 0;
    float: right;
    clear: both;
}
.chat-bubble-assistant {
    background: #f1f0f0;
    color: black;
    padding: 0.8rem 1rem;
    border-radius: 15px 15px 15px 0;
    max-width: 70%;
    margin: 5px 0;
    float: left;
    clear: both;
}
.intro-box {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    color: white;
    text-align: center;
    padding: 2rem;
    border-radius: 10px;
    margin-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Initialisation de la session
# -----------------------------
if "historique" not in st.session_state:
    st.session_state.historique = []
if "show_intro" not in st.session_state:
    st.session_state.show_intro = True

# -----------------------------
# Template pour GPT -> SQL
# -----------------------------
template = """Tu es un expert SQL pour MySQL.
Transforme la question en français en requête SQL valide.

Tables disponibles:
- produit(Id, UNITE, DESIGNATION, Nom_Produit, prix_achat)
- client(ID_CLIENT, Nom_CLIENT, VILLE, REGION, MAGASIN, Telephone)
- ventes(Id_vente, QTE, DATE, N_BL, MT_TTC, PU_TTC, id_prod, ID_CLIENT, ID_paiement)
- paiement(ID_paiement, DATE, N_BL, ID_CLIENT, MODE_PAIEMENT, MONTANT_REGLE, MONTANT_TOTAL, RELIQUAT)

Règles:
- Utilise les noms EXACTS des colonnes
- Jointures: ventes.id_prod = produit.Id, ventes.ID_CLIENT = client.ID_CLIENT, ventes.ID_paiement = paiement.ID_paiement
- Réponds UNIQUEMENT avec du SQL pur, pas d’explication

Question: {question}
SQL:"""

# -----------------------------
# Générer SQL via GPT
# -----------------------------
def generer_sql(question):
    prompt = template.format(question=question)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un expert SQL qui convertit des questions en français en requêtes SQL MySQL."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=300
    )
    sql = response.choices[0].message.content.strip()
    return sql

# -----------------------------
# Exécution SQL MySQL
# -----------------------------
def execute_query(sql):
    sql = sql.strip()
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    if sql.startswith("```"):
        sql = sql.replace("```", "").strip()

    conn = None
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="kawla2003",
            database="gestion_ventes",
            port=3306
        )
        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.description:
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            df = pd.DataFrame(rows, columns=columns)
            return df, f"{len(rows)} résultat(s) trouvé(s)", True
        else:
            conn.commit()
            return None, "Requête exécutée avec succès.", True
    except mysql.connector.Error as e:
        return None, f"Erreur MySQL : {e}", False
    except Exception as e:
        return None, f"Erreur générale : {e}", False
    finally:
        if conn:
            conn.close()

# -----------------------------
# Sidebar
# -----------------------------
# -----------------------------
# Sidebar
# -----------------------------
# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## 📊 Tableau de Bord")

    # Bouton pour réinitialiser le chat
    if st.button("🆕 Nouveau Chat"):
        st.session_state.historique = []      # vider l'historique
        st.session_state.show_intro = True    # réafficher l'intro
        if "current_results" in st.session_state:
            del st.session_state["current_results"]

    # Affichage de l'historique
    if st.session_state.historique:
        for i, item in enumerate(reversed(st.session_state.historique)):
            idx = len(st.session_state.historique) - i - 1
            status_icon = "✅" if item['success'] else "❌"
            
            with st.expander(f"{status_icon} Question #{idx+1}", expanded=False):
                if item['result_df'] is not None and len(item['result_df']) > 0:
                    st.markdown(f"**Résultats:** {len(item['result_df'])} ligne(s)")
                    if len(item['result_df']) <= 5:
                        st.dataframe(item['result_df'], use_container_width=True)
                    else:
                        st.markdown("Aperçu (5 premières lignes):")
                        st.dataframe(item['result_df'].head(), use_container_width=True)
                st.markdown(f"**Statut:** {item['result_msg']}")
                st.caption(f"🕒 {item['timestamp']}")
                
                # Charger les résultats dans la session si besoin
                if st.button(f"Charger les résultats #{idx+1}", key=f"load_{idx}"):
                    st.session_state.current_results = (
                        item['result_df'],
                        item['result_msg'],
                        item['success'],
                        item['question'],
                        item['sql'],
                        item['timestamp']
                    )
                    st.session_state.show_results = True

# -----------------------------
# Affichage intro ou chat
# -----------------------------
if st.session_state.show_intro:
    st.markdown("""
    <div class="intro-box">
        <h1>🔍 Assistant SQL Intelligent</h1>
        <p>Prenez vos questions en français, obtenez du SQL MySQL automatiquement</p>
        <p>💭 Posez votre question</p>
    </div>
    """, unsafe_allow_html=True)

# Affichage du chat depuis l'historique
for item in st.session_state.historique:
    # Question utilisateur
    st.markdown(f"<div class='chat-bubble-user'>{item['question']}</div>", unsafe_allow_html=True)
    
    # Réponse assistant
    if item["result_df"] is not None and len(item["result_df"]) > 0:
        st.dataframe(item["result_df"], use_container_width=True, hide_index=True)
    else:
        st.markdown(f"<div class='chat-bubble-assistant'>{item['result_msg']}</div>", unsafe_allow_html=True)

# -----------------------------
# Zone de saisie (chat input)
# -----------------------------
question = st.chat_input("Posez votre question en français...")
if question:
    with st.spinner("🤖 Génération et exécution en cours..."):
        sql_query = generer_sql(question)
        result_df, result_msg, success = execute_query(sql_query)

    # Sauvegarder dans l'historique
    st.session_state.historique.append({
        "question": question,
        "sql": sql_query,
        "result_df": result_df,
        "result_msg": result_msg,
        "success": success,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })

    # Cacher l’intro après la première question
    st.session_state.show_intro = False

    st.rerun()
