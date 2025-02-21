import streamlit as st
from pydub import AudioSegment
from dotenv import dotenv_values
from hashlib import md5
from openai import OpenAI
from io import BytesIO
import base64
from qdrant_client import QdrantClient

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

    
env = dotenv_values(".env")

AUDIO_TRANSCRIBE_MODEL = "whisper-1"

@st.cache_resource
def get_openai_client():
    return OpenAI(api_key=st.session_state["openai_api_key"])

def transcribe_audio(audio_bytes):
    openai_client = get_openai_client()
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.mp3"
    transcript = openai_client.audio.transcriptions.create(
        file=audio_file,
        model=AUDIO_TRANSCRIBE_MODEL,
        response_format="srt",
    )

    return transcript

@st.cache_resource
def get_qdrant_client():
    return QdrantClient(
    url=env["QDRANT_URL"], 
    api_key=env["QDRANT_API_KEY"],
)

# Tytuł aplikacji
st.title("App'ka do generowania napisów")
# Ścieżki do obrazów
image_path_1 = "obrazek1.png"  # Ścieżka do pierwszego obrazu
image_path_2 = "obrazek2.png"  # Ścieżka do drugiego obrazu

# Konwertowanie obrazu na Base64
# Konwertowanie obrazów na Base64
image_base64_1 = image_to_base64(image_path_1)
image_base64_2 = image_to_base64(image_path_2)

# Ustawienie dwóch obrazków jako tła
st.markdown(
    f"""
    <style>
        .stApp {{
            height: 100vh;  /* Wysokość na cały ekran */
            background-image: 
                url("data:image/png;base64,{image_base64_1}"),  /* Pierwszy obraz */
                url("data:image/png;base64,{image_base64_2}");  /* Drugi obraz */
            background-size: contain, contain;  /* Oba obrazy mają rozmiar 'contain' */
            background-repeat: no-repeat, no-repeat;  /* Obrazy się nie powtarzają */
            background-position: left center, right center;  /* Pierwszy obraz po lewej, drugi po prawej */
            background-attachment: fixed, fixed;  /* Obrazy mają być stałe przy przewijaniu */
        }}
    </style>
    """, 
    unsafe_allow_html=True
)
# OpenAI API key protection
if not st.session_state.get("openai_api_key"):
    if "OPENAI_API_KEY" in env:
        st.session_state["openai_api_key"] = env["OPENAI_API_KEY"]

    else:
        st.info("Dodaj swój klucz API OpenAI aby móc korzystać z tej aplikacji")
        st.session_state["openai_api_key"] = st.text_input("Klucz API", type="password")
        if st.session_state["openai_api_key"]:
            st.rerun()

if not st.session_state.get("openai_api_key"):
    st.stop()




if "uploaded_file" not in st.session_state or st.session_state["uploaded_file"] is None:
    st.session_state["note_audio_bytes"] = None
    st.session_state["note_audio_text"] = ""
    st.session_state["note_audio_bytes_md5"] = None
    st.session_state["note_text"] = ""
    st.session_state["transcription_saved"] = False
    

# Funkcja do wgrywania pliku
st.markdown(
    """
    <style>
        .stFileUploader {
            background-color: black;
            color: white;
            padding: 12px;
            border: 10px solid black;
            border-radius: 10px;
            font-size: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True
)
uploaded_file = st.file_uploader("Wybierz plik", type="mp4")

# Jeśli plik został załadowany, zapisujemy go w sesji
if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file
    st.success("Plik został załadowany!")

# Jeśli plik jest już załadowany, wyświetlamy przycisk do jego podmiany
if 'uploaded_file' in st.session_state and st.session_state.uploaded_file is not None:
    # Możliwość usunięcia pliku (podmiana)
    
    st.markdown(
    """
    <div style="background-color: black; color: white; padding: 12px;">
        Jeśli chcesz załadować inny plik kliknij w przycisk 'Zmień plik'
    </div>
    """,
    unsafe_allow_html=True
)
    change_file = st.button("Zmień plik")

    if change_file:
        # Usunięcie/podmiana pliku
        st.session_state.uploaded_file = None
        st.warning("Plik został usunięty. Możesz załadować nowy.")
        # Po usunięciu pliku, umożliwiamy ponowne wgranie
        st.stop()

    # Zawsze wyświetlaj film
    st.video(st.session_state.uploaded_file)

    # Obsługa ekstrakcji audio
    if st.button("Wyodrębnij audio") and st.session_state.get("note_audio_bytes") is None:
        # Zapisanie wideo jako tymczasowy plik
        with open("uploaded_video.mp4", "wb") as f:
            f.write(st.session_state.uploaded_file.getbuffer())

        

        note_audio = AudioSegment.from_file("uploaded_video.mp4")


        if note_audio:
            audio = BytesIO()
            note_audio.export(audio, format="mp3")
            # Wyświetlenie informacji o sukcesie
            st.success("Audio zostało wyodrębnione i zapisane jako MP3.")
            st.session_state["note_audio_bytes"] = audio.getvalue()
            current_md5 = md5(st.session_state["note_audio_bytes"]).hexdigest()
            if st.session_state["note_audio_bytes_md5"] != current_md5:
                st.session_state["note_audio_text"] = ""
                st.session_state["note_audio_bytes_md5"] = current_md5


    if st.session_state.get("note_audio_bytes"):
        st.audio(st.session_state["note_audio_bytes"], format="audio/mp3")


    if st.session_state["note_audio_bytes"]:
        if st.button("Transkrybuj audio"):
            st.session_state["note_audio_text"] = transcribe_audio(st.session_state["note_audio_bytes"])
            
    
    # Wyświetlamy transkrybcję
    st.markdown(
    """
    <style>
        .stTextArea label {
            color: white;
            background-color: black;
            padding: 12px;
            font-size: 20px;
        }
    </style>
    """, 
    unsafe_allow_html=True
)
    if st.session_state["note_audio_text"]:
        st.session_state["note_text"] = st.text_area("Edytuj transkrybcję", value=st.session_state["note_audio_text"], height=500)

    if st.session_state["note_text"] and st.button("Zapisz transkrybcję", disabled=not st.session_state["note_text"]):
        note_text = st.session_state["note_text"]
        st.session_state["transcription_saved"] = True
        
        # Zapisujemy transkrybcję do pliku SRT
        srt_napisy = st.session_state["note_text"]

        with open("audio.srt", "w") as f:
            f.write(srt_napisy)

        st.success("Transkrybcja została zapisana do pliku audio.srt")

        audio_path = "audio.mp3"
        with open(audio_path, "wb") as f:
            f.write(st.session_state["note_audio_bytes"])



col1, col2 = st.columns([15, 5])

with col1:

    # Pokazujemy przyciski do pobrania tylko po zapisaniu transkrypcji
    if st.session_state["transcription_saved"]:
        # Pobranie napisów
        with open("audio.srt", "rb") as f:
            srt_file = f.read()

    

        # Przycisk do pobrania plików
        if st.download_button(
            label="Pobierz napisy (SRT)",
            data=srt_file,
            file_name="audio.srt",
            mime="application/octet-stream",
        ):
            st.success("Pobrałeś napisy, sprawdź folder Pobrane.")
with col2:
    if st.session_state["transcription_saved"]:
        with open("audio.mp3", "rb") as f:
            mp3_file = f.read()

        if st.download_button(
            label="Pobierz audio (MP3)",
            data=mp3_file,
            file_name="audio.mp3",
            mime="audio/mp3",
        ):
            st.success("Brawo, pobrałeś audio, sprawdź folder Pobrane.")



