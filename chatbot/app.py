import psycopg2
from openai import OpenAI
import pandas as pd
import streamlit as st
from datetime import datetime
# -*- coding: utf-8 -*-

# Configuration
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Configuration de la page
st.set_page_config(
    page_title="Assistant SQL Intelligent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour améliorer l'apparence
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .query-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .result-card {
        background: #e8f5e8;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    
    .stats-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .sidebar-section {
        background: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de l'état de session
if 'historique' not in st.session_state:
    st.session_state.historique = []

# Template pour GPT
template = """Tu es un expert SQL pour PostgreSQL. Transforme la question en français en requête SQL.

Tables disponibles:
- produit("Id", "UNITE", "DESIGNATION", "Nom_Produit", prix_achat)
- client("ID_CLIENT", "Nom_CLIENT", "VILLE", "REGION", "MAGASIN", "Telephone")
- ventes("Id_vente", "QTE", "DATE", "N_BL", "MT_TTC", "PU_TTC", id_prod, "ID_CLIENT", "ID_paiement")
- paiement("ID_paiement", "DATE", "N_BL", "ID_CLIENT", "MODE_PAIEMENT", "MONTANT_REGLE", "MONTANT_TOTAL", "RELIQUAT")

Règles:
- Utilise les noms EXACTS des colonnes avec guillemets doubles
- Jointures: ventes.id_prod = produit."Id", ventes."ID_CLIENT" = client."ID_CLIENT", ventes."ID_paiement" = paiement."ID_paiement"
- Réponds UNIQUEMENT avec du SQL pur, pas d'explication

Exemples:
Question: "Les 10 produits les plus vendus"
SQL: SELECT p."Nom_Produit", p."DESIGNATION", SUM(v."QTE") as total_vendu FROM ventes v JOIN produit p ON v.id_prod = p."Id" GROUP BY p."Nom_Produit", p."DESIGNATION", p."Id" ORDER BY total_vendu DESC LIMIT 10;

Question: "Chiffre d'affaires total"
SQL: SELECT SUM("MT_TTC") as chiffre_affaires_total FROM ventes;

Question: "Les 5 meilleurs clients"
SQL: SELECT c."Nom_CLIENT", c."VILLE", SUM(v."MT_TTC") as total_achats FROM ventes v JOIN client c ON v."ID_CLIENT" = c."ID_CLIENT" GROUP BY c."Nom_CLIENT", c."VILLE", c."ID_CLIENT" ORDER BY total_achats DESC LIMIT 5;

Question: {question}
SQL:"""

def generer_sql(question):
    """Génère du SQL à partir d'une question en français"""
    prompt = template.format(question=question)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un expert SQL qui convertit des questions en français en requêtes SQL."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=300
        )
        
        sql = response.choices[0].message.content.strip()
        return sql
    except Exception as e:
        st.error(f"Erreur OpenAI: {e}")
        return None

def execute_query(sql):
    """Exécute une requête SQL sur PostgreSQL"""
    # Nettoyer le SQL généré
    sql = sql.strip()
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    if sql.startswith("```"):
        sql = sql.replace("```", "").strip()
    
    conn = None
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="suivi_ventes",
            user="airbyte_user",
            password="kawla2003",
            options="-c client_encoding=UTF8"
        )
        cursor = conn.cursor()
        
        cursor.execute(sql)
        
        if cursor.description: 
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # Retourner les résultats sous forme de DataFrame
            df = pd.DataFrame(rows, columns=columns)
            return df, f"{len(rows)} résultat(s) trouvé(s)", True
        else:
            conn.commit()
            return None, "Requête exécutée avec succès.", True
            
    except psycopg2.Error as e:
        return None, f"Erreur PostgreSQL : {e}", False
    except Exception as e:
        return None, f"Erreur générale : {e}", False
    finally:
        if conn:
            conn.close()

# En-tête principal
st.markdown("""
<div class="main-header">
    <h1>🔍 Assistant SQL Intelligent</h1>
    <p>Posez vos questions en français, obtenez du SQL automatiquement</p>
</div>
""", unsafe_allow_html=True)

# Sidebar avec informations et historique
with st.sidebar:
    st.markdown("## 📊 Tableau de Bord")
    
    # Statistiques dans des cartes
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stats-card">
            <h3 style="margin:0; color:#667eea;">Questions</h3>
            <h2 style="margin:0;">{len(st.session_state.historique)}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        succes = sum(1 for item in st.session_state.historique if item['success'])
        st.markdown(f"""
        <div class="stats-card">
            <h3 style="margin:0; color:#28a745;">Succès</h3>
            <h2 style="margin:0;">{succes}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Boutons d'action
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Effacer", use_container_width=True):
            st.session_state.historique = []
            st.rerun()
    
    with col2:
        if st.button("💾 Exporter", use_container_width=True):
            if st.session_state.historique:
                # Créer un DataFrame avec l'historique
                export_data = []
                for item in st.session_state.historique:
                    export_data.append({
                        "Question": item['question'],
                        "SQL": item['sql'],
                        "Statut": "Succès" if item['success'] else "Erreur",
                        "Timestamp": item['timestamp']
                    })
                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="📥 Télécharger CSV",
                    data=csv,
                    file_name=f"historique_sql_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    st.markdown("---")
    
    # Historique des requêtes
    st.markdown("## 📋 Historique des Requêtes")
    
    if st.session_state.historique:
        for i, item in enumerate(reversed(st.session_state.historique)):
            idx = len(st.session_state.historique) - i - 1
            status_icon = "✅" if item['success'] else "❌"
            
            with st.expander(f"{status_icon} Question #{idx+1}", expanded=False):
                st.markdown(f"**Question:** {item['question']}")
                st.code(item['sql'], language="sql")
                
                if item['result_df'] is not None and len(item['result_df']) > 0:
                    st.markdown(f"**Résultats:** {len(item['result_df'])} ligne(s)")
                    if len(item['result_df']) <= 5:
                        st.dataframe(item['result_df'], use_container_width=True)
                    else:
                        st.markdown("Aperçu (5 premières lignes):")
                        st.dataframe(item['result_df'].head(), use_container_width=True)
                
                st.markdown(f"**Statut:** {item['result_msg']}")
                st.caption(f"🕒 {item['timestamp']}")
    else:
        st.info("Aucune requête dans l'historique")

# Interface principale
col1, col2 = st.columns([3, 1])

with col1:
    # Zone de saisie de question avec design amélioré
    st.markdown("### 💭 Posez votre question")
    question = st.text_area(
        "Décrivez ce que vous voulez analyser en français naturel:",
        placeholder="Exemples:\n• Les 10 produits les plus vendus ce mois\n• Quel client a généré le plus de chiffre d'affaires?\n• Combien avons-nous vendu en décembre 2023?",
        height=100,
        key="question_main"
    )

with col2:
    st.markdown("### 🚀 Action")
    st.markdown("<br>", unsafe_allow_html=True)  # Espace pour aligner
    
    if st.button("🔍 Analyser", type="primary", use_container_width=True):
        if question.strip():
            try:
                with st.spinner("🤖 Génération de la requête SQL..."):
                    # Générer le SQL
                    sql_query = generer_sql(question)
                    
                    if sql_query:
                        # Exécuter la requête
                        with st.spinner("⚡ Exécution de la requête..."):
                            result_df, result_msg, success = execute_query(sql_query)
                        
                        # Ajouter à l'historique
                        st.session_state.historique.append({
                            "question": question,
                            "sql": sql_query,
                            "result_df": result_df,
                            "result_msg": result_msg,
                            "success": success,
                            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        })
                        
                        # Afficher les résultats avec un design amélioré
                        st.markdown("---")
                        
                        # Requête SQL générée
                        st.markdown("### 📝 Requête SQL Générée")
                        st.markdown(f"""
                        <div class="query-card">
                            <p><strong>Question:</strong> {question}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.code(sql_query, language="sql")
                        
                        # Résultats
                        if result_df is not None:
                            st.markdown("### 📊 Résultats de l'Analyse")
                            
                            # Afficher les métriques si approprié
                            if len(result_df) > 0:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Nombre de lignes", len(result_df))
                                with col2:
                                    st.metric("Nombre de colonnes", len(result_df.columns))
                                with col3:
                                    if any(result_df.dtypes == 'object'):
                                        numeric_cols = result_df.select_dtypes(include=['number']).columns
                                        if len(numeric_cols) > 0:
                                            total = result_df[numeric_cols].sum().sum() if len(numeric_cols) > 0 else 0
                                            st.metric("Somme totale", f"{total:,.2f}" if total > 0 else "N/A")
                            
                            # Tableau des résultats
                            st.dataframe(
                                result_df, 
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            # Options d'export
                            if len(result_df) > 0:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    csv = result_df.to_csv(index=False)
                                    st.download_button(
                                        "📥 Télécharger CSV",
                                        csv,
                                        file_name=f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv",
                                        use_container_width=True
                                    )
                                
                                with col2:
                                    if st.button("📈 Créer un graphique", use_container_width=True):
                                        # Suggérer des visualisations basées sur les données
                                        numeric_cols = result_df.select_dtypes(include=['number']).columns
                                        if len(numeric_cols) > 0:
                                            st.info("💡 Suggestion: Utilisez les colonnes numériques pour créer des graphiques avec st.bar_chart() ou st.line_chart()")
                        
                        if success:
                            st.success(f"✅ {result_msg}")
                        else:
                            st.error(f"❌ {result_msg}")
                            
            except Exception as e:
                st.error(f"❌ Erreur inattendue: {e}")
        else:
            st.warning("⚠️ Veuillez saisir une question avant de continuer.")

# Section d'aide et exemples
with st.expander("💡 Exemples de questions que vous pouvez poser", expanded=False):
    st.markdown("""
    **📈 Analyses de ventes:**
    - Les 10 produits les plus vendus
    - Chiffre d'affaires par mois
    - Évolution des ventes par région
    
    **👥 Analyses clients:**
    - Les 5 meilleurs clients
    - Clients par région
    - Répartition par mode de paiement
    
    **💰 Analyses financières:**
    - Chiffre d'affaires total
    - Marges par produit
    - Impayés et reliquats
    
    **📅 Analyses temporelles:**
    - Ventes du mois dernier
    - Comparaison année sur année
    - Tendances saisonnières
    """)

# Section informations sur les tables
with st.expander("🗃️ Structure de la base de données", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Table: produit**
        - Id (Identifiant)
        - UNITE (Unité de mesure)
        - DESIGNATION (Description)
        - Nom_Produit (Nom du produit)
        - prix_achat (Prix d'achat)
        
        **Table: client**
        - ID_CLIENT (Identifiant client)
        - Nom_CLIENT (Nom du client)
        - VILLE (Ville)
        - REGION (Région)
        - MAGASIN (Magasin)
        - Telephone (Téléphone)
        """)
    
    with col2:
        st.markdown("""
        **Table: ventes**
        - Id_vente (Identifiant vente)
        - QTE (Quantité)
        - DATE (Date de vente)
        - N_BL (Numéro bon de livraison)
        - MT_TTC (Montant TTC)
        - PU_TTC (Prix unitaire TTC)
        - id_prod (Référence produit)
        - ID_CLIENT (Référence client)
        - ID_paiement (Référence paiement)
        
        **Table: paiement**
        - ID_paiement (Identifiant paiement)
        - DATE (Date de paiement)
        - N_BL (Numéro bon de livraison)
        - ID_CLIENT (Référence client)
        - MODE_PAIEMENT (Mode de paiement)
        - MONTANT_REGLE (Montant réglé)
        - MONTANT_TOTAL (Montant total)
        - RELIQUAT (Reste à payer)
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    🤖 Assistant SQL Intelligent | Propulsé par GPT-4o Mini & PostgreSQL
</div>
""", unsafe_allow_html=True)