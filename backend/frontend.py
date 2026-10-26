import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="ЧатЖопа", page_icon="🤖", layout="wide")

# --- Инициализация памяти ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "character_id" not in st.session_state:
    st.session_state.character_id = None # ID персонажа для НОВОГО чата

# --- Функции запросов к API ---
def fetch_conversations():
    try:
        r = requests.get(f"{API_URL}/conversations")
        return r.json() if r.status_code == 200 else []
    except:
        return []

def fetch_characters():
    try:
        r = requests.get(f"{API_URL}/characters")
        return r.json() if r.status_code == 200 else []
    except:
        return []

def load_messages(conv_id):
    try:
        r = requests.get(f"{API_URL}/conversations/{conv_id}/messages")
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

# --- БОКОВАЯ ПАНЕЛЬ (SIDEBAR) ---
with st.sidebar:
    st.info("Пользователь: **web_user**")
    
    # Блок создания нового чата с персонажем
    st.header("Новый диалог")
    characters = fetch_characters()
    
    if characters:
        if st.button("Начать чат", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.session_state.character_id = selected_char_id # Запоминаем, с кем говорим
            
            # (Опционально) Можно автоматически подгрузить первое сообщение персонажа
            # char_info = next((c for c in characters if c["id"] == selected_char_id), None)
            # if char_info and char_info.get("first_message"):
            #     st.session_state.messages.append({"role": "assistant", "content": char_info["first_message"]})
            
            st.rerun()

        # Создаем словарь {id: имя} для селектбокса
        char_options = {c["id"]: c["name"] for c in characters}
        
        selected_char_id = st.selectbox(
            "Выберите персонажа:",
            options=list(char_options.keys()),
            format_func=lambda x: char_options[x]
        )
        
        
    else:
        st.warning("В базе нет персонажей! Создайте их через Swagger (/docs).")

    st.divider()
    
    # Блок истории чатов
    st.header("История")
    conversations = fetch_conversations()
    
    if conversations:
        options = {c["id"]: f"{c['title']}" for c in conversations}
        
        current_index = None
        if st.session_state.conversation_id in options:
            current_index = list(options.keys()).index(st.session_state.conversation_id)
            
        selected_id = st.selectbox(
            "Ваши старые чаты:",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            index=current_index,
            placeholder="Выберите чат..."
        )
        
        if selected_id is not None and selected_id != st.session_state.conversation_id:
            st.session_state.conversation_id = selected_id
            st.session_state.messages = load_messages(selected_id)
            st.session_state.character_id = None # Сбрасываем, так как персонаж уже привязан к старому чату
            st.rerun()

# --- ОСНОВНОЙ ЭКРАН ---
st.title("ЧатЖопа")

# Показываем, с кем идет диалог (если это новый чат с персонажем)
if st.session_state.character_id and characters:
    char_name = next((c["name"] for c in characters if c["id"] == st.session_state.character_id), "Неизвестный")
    st.caption(f"Вы начинаете новый диалог с персонажем: **{char_name}**")
elif st.session_state.conversation_id:
    st.caption(f"ID текущего диалога: {st.session_state.conversation_id}")

# Отображение истории
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Поле ввода
if prompt := st.chat_input("Напишите сообщение..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Собираем данные для FastAPI
    payload = {
        "message": prompt,
        "conversation_id": st.session_state.conversation_id,
        "character_id": st.session_state.character_id # Передаем ID персонажа!
    }

    with st.spinner("Персонаж печатает..."):
        try:
            response = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            answer = data["reply"]
            # Сервер возвращает ID созданного/существующего чата
            st.session_state.conversation_id = data["conversation_id"]
            # После создания первого сообщения сбрасываем character_id, 
            # так как теперь чат привязан к персонажу в базе
            st.session_state.character_id = None 
            
        except requests.exceptions.RequestException as e:
            answer = f"Ошибка: {e}"
            st.error(answer)
            st.session_state.messages.pop()
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
        
    st.rerun()