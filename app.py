import streamlit as st 
import pandas as pd
import json
import os
from datetime import datetime

# -----------------------------
# Config
# -----------------------------
CSV_URL = "https://raw.githubusercontent.com/joynaomi81/Data-Curation/refs/heads/main/english_only.csv"
PROGRESS_FILE = "user_progress.json"
ADMIN_PASSWORD = st.secrets["admin"]["password"]

# -----------------------------
# Helpers
# -----------------------------
def load_sentences():
    df = pd.read_csv(CSV_URL)
    if "English" not in df.columns:
        st.error("CSV must contain an 'English' column.")
        st.stop()
    return df["English"].tolist()

def load_user_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)

        # ✅ Ensure backward compatibility (fix KeyError issues)
        for user, details in data.items():
            if "translations" not in details:
                details["translations"] = {}
            if "metadata" not in details:
                details["metadata"] = {}
            if "assigned" not in details:
                details["assigned"] = []
            if "index" not in details:
                details["index"] = 0
        return data
    return {}

def save_user_progress(data):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -----------------------------
# Metadata Page
# -----------------------------
def metadata_page(username):
    st.subheader("📝 User Metadata")

    all_progress = load_user_progress()
    user_data = all_progress.get(username, {})
    metadata = user_data.get("metadata", {})

    name = st.text_input("Full Name", metadata.get("name", ""))
    sex = st.selectbox(
        "Sex", ["Male", "Female", "Other"],
        index=["Male", "Female", "Other"].index(metadata.get("sex", "Male"))
    )
    age = st.number_input("Age", min_value=10, max_value=120, value=metadata.get("age", 18))
    gmail = st.text_input("Gmail", metadata.get("gmail", ""))
    country = st.text_input("Country", metadata.get("country", ""))

    if st.button("Save Metadata"):
        user_data["metadata"] = {
            "name": name,
            "sex": sex,
            "age": age,
            "gmail": gmail,
            "country": country
        }
        all_progress[username] = user_data
        save_user_progress(all_progress)
        st.success("✅ Metadata saved successfully!")

        # Auto move to Translate page
        st.session_state.page = "Translate"
        st.rerun()

# -----------------------------
# Translation Page
# -----------------------------
def translation_page(username):
    st.subheader("🌍 Translate Sentences")

    sentences = load_sentences()
    all_progress = load_user_progress()

    if username not in all_progress:
        all_progress[username] = {
            "index": 0,
            "translations": {},
            "metadata": {},
            "assigned": []
        }

    user_data = all_progress[username]

    # Assign 100 unique sentences if not already assigned
    if not user_data.get("assigned"):
        all_users = list(all_progress.keys())
        user_index = all_users.index(username)
        start_idx = user_index * 100
        end_idx = min(start_idx + 100, len(sentences))
        user_data["assigned"] = list(range(start_idx, end_idx))
        all_progress[username] = user_data
        save_user_progress(all_progress)

    assigned_indices = user_data["assigned"]
    current_idx = user_data.get("index", 0)

    # Show user progress
    translated_count = len(user_data.get("translations", {}))
    total_assigned = len(assigned_indices)
    st.info(f"📊 Progress: {translated_count}/{total_assigned} sentences translated "
            f"({(translated_count/total_assigned)*100:.1f}%)")

    if current_idx >= total_assigned:
        st.success("🎉 You have completed all your assigned translations! Thank you.")
        return

    sentence_idx = assigned_indices[current_idx]
    sentence = sentences[sentence_idx]
    st.info(f"**Sentence {current_idx + 1}/{total_assigned}:** {sentence}")

    input_key = f"translation_{username}_{current_idx}"
    translation = st.text_area("Your Translation", key=input_key)

    if st.button("Submit Translation"):
        if translation.strip() == "":
            st.warning("⚠️ Please enter a translation before submitting.")
        else:
            # ✅ Ensure translations dictionary exists
            if "translations" not in user_data:
                user_data["translations"] = {}

            user_data["translations"][str(sentence_idx)] = {
                "English": sentence,
                "Translation": translation.strip(),
                "Timestamp": datetime.now().isoformat()
            }
            user_data["index"] = current_idx + 1
            all_progress[username] = user_data
            save_user_progress(all_progress)
            st.success("✅ Translation submitted! Moving to next sentence...")
            st.rerun()

# -----------------------------
# Admin Page
# -----------------------------
def admin_page():
    st.subheader("🛡️ Admin Dashboard")

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        password = st.text_input("Enter Admin Password", type="password")
        if st.button("Login as Admin"):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("✅ Welcome, Admin!")
                st.rerun()
            else:
                st.error("❌ Incorrect password.")
        return

    data = load_user_progress()
    if not data:
        st.info("No user data yet.")
        return

    progress_data = []
    metadata_rows = []
    translation_rows = []

    for user, details in data.items():
        translations = details.get("translations", {})
        metadata = details.get("metadata", {})
        assigned = details.get("assigned", [])

        progress_data.append({
            "User": user,
            "Translated": len(translations),
            "Assigned": len(assigned),
            "Progress (%)": round((len(translations)/len(assigned))*100, 2) if assigned else 0
        })

        metadata_rows.append({
            "User": user,
            "Name": metadata.get("name", ""),
            "Sex": metadata.get("sex", ""),
            "Age": metadata.get("age", ""),
            "Gmail": metadata.get("gmail", ""),
            "Country": metadata.get("country", "")
        })

        for idx, entry in translations.items():
            translation_rows.append({
                "User": user,
                "Index": idx,
                "English": entry["English"],
                "Translation": entry["Translation"],
                "Timestamp": entry["Timestamp"]
            })

    if progress_data:
        st.subheader("📊 User Progress Overview")
        st.dataframe(pd.DataFrame(progress_data))

    if metadata_rows:
        st.subheader("👤 User Metadata")
        metadata_df = pd.DataFrame(metadata_rows)
        st.dataframe(metadata_df)
        st.download_button(
            "📥 Download Metadata (CSV)",
            metadata_df.to_csv(index=False).encode("utf-8"),
            "user_metadata.csv",
            "text/csv"
        )

    if translation_rows:
        st.subheader("📜 User Translations")
        translation_df = pd.DataFrame(translation_rows)
        st.dataframe(translation_df)
        st.download_button(
            "📥 Download Translations (CSV)",
            translation_df.to_csv(index=False).encode("utf-8"),
            "user_translations.csv",
            "text/csv"
        )

# -----------------------------
# Main
# -----------------------------
def main():
    st.title("🌍 Yorlect Data Curation Platform")

    if "username" not in st.session_state:
        st.session_state.username = None
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "page" not in st.session_state:
        st.session_state.page = "Login"

    menu = ["Login", "Metadata", "Translate", "Admin", "Refresh", "About"]
    choice = st.sidebar.selectbox("Menu", menu, index=menu.index(st.session_state.page))
    st.session_state.page = choice

    if st.session_state.page == "Login":
        if not st.session_state.logged_in:
            username = st.text_input("Enter your username")
            if st.button("Login"):
                if username.strip():
                    st.session_state.username = username.strip()
                    st.session_state.logged_in = True
                    st.success(f"🎉 Welcome, {username}!")
                    st.session_state.page = "Metadata"
                    st.rerun()
                else:
                    st.error("Please enter a valid username.")
        else:
            st.info(f"✅ Logged in as {st.session_state.username}")
            if st.button("Next →"):
                st.session_state.page = "Metadata"
                st.rerun()

    elif st.session_state.page == "Metadata":
        if st.session_state.logged_in:
            metadata_page(st.session_state.username)
        else:
            st.warning("Please login first.")

    elif st.session_state.page == "Translate":
        if st.session_state.logged_in:
            translation_page(st.session_state.username)
        else:
            st.warning("Please login first.")

    elif st.session_state.page == "Admin":
        admin_page()

    elif st.session_state.page == "Refresh":
        st.session_state.clear()
        st.success("🔄 App refreshed.")
        st.rerun()

    elif st.session_state.page == "About":
        st.subheader("ℹ️ About This App")
        st.write("""
        This is a **Data Curation Web App** built with Streamlit.  
        - Users log in, provide metadata, and translate **100 unique sentences**.  
        - Progress is saved so they can continue anytime.  
        - Admin can log in securely, monitor user progress, and download both **metadata** and **translations** separately.  
        - Built for collaborative language resource creation 🌍.
        """)

if __name__ == "__main__":
    main()
