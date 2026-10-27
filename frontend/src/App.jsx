import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import './App.css';

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [characters, setCharacters] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  
  const [selectedCharId, setSelectedCharId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [viewingChar, setViewingChar] = useState(null);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // --- СОСТОЯНИЯ ДЛЯ РЕДАКТИРОВАНИЯ КАРТОЧКИ ---
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editFormData, setEditFormData] = useState({});

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "", description: "", personality: "", scenario: "", first_message: ""
  });

  const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

  useEffect(() => {
    fetchCharacters();
    fetchConversations();
  }, []);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // --- ФУНКЦИИ ЗАГРУЗКИ ---
  const fetchCharacters = async () => {
    try {
      const res = await fetch(`${API_URL}/characters`);
      const data = await res.json();
      setCharacters(data);
    } catch (e) { console.error(e); }
  };

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_URL}/conversations`);
      const data = await res.json();
      setConversations(data);
    } catch (e) { console.error(e); }
  };

  const loadMessages = async (convId) => {
    try {
      const res = await fetch(`${API_URL}/conversations/${convId}/messages`);
      const data = await res.json();
      setMessages(data);
      setConversationId(convId);
      setSelectedCharId(null);
      setViewingChar(null);
      setIsEditingProfile(false); // Закрываем режим редактирования
    } catch (e) { console.error(e); }
  };

  // --- УПРАВЛЕНИЕ КАРТОЧКОЙ ---
  const handleCharClick = (char) => {
    setViewingChar(char);
    setConversationId(null);
    setSelectedCharId(null);
    setMessages([]);
    setIsEditingProfile(false); // При открытии нового персонажа выключаем редактирование
  };

  const startChatWithChar = () => {
    if (!viewingChar) return;
    setSelectedCharId(viewingChar.id);
    setViewingChar(null);
    setIsEditingProfile(false);
    
    if (viewingChar.first_message) {
      setMessages([{ role: "assistant", content: viewingChar.first_message }]);
    } else {
      setMessages([]);
    }
  };

  // --- РЕДАКТИРОВАНИЕ ПЕРСОНАЖА ---
  const startEditingProfile = () => {
    setEditFormData(viewingChar); // Копируем данные текущего персонажа в форму
    setIsEditingProfile(true);
  };

  const handleEditChange = (e) => {
    setEditFormData({ ...editFormData, [e.target.name]: e.target.value });
    
    e.target.style.height = 'auto';
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  const handleUpdateCharacter = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/characters/${viewingChar.id}`, {
        method: 'PATCH', // Используем PATCH, который ты написал на бэкенде
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editFormData)
      });
      
      if (res.ok) {
        const updatedChar = await res.json();
        setViewingChar(updatedChar); // Обновляем карточку справа
        setIsEditingProfile(false);  // Выключаем режим редактирования
        fetchCharacters();           // Обновляем список слева (чтобы имя обновилось)
      }
    } catch (error) {
      alert("Ошибка при обновлении персонажа");
    }
  };

  // --- ФУНКЦИИ УДАЛЕНИЯ ---
  const deleteChat = async (e, id) => {
    e.stopPropagation(); 
    if (!window.confirm("Удалить этот чат?")) return;
    try {
      await fetch(`${API_URL}/conversations/${id}`, { method: 'DELETE' });
      fetchConversations(); 
      if (conversationId === id) {
        setConversationId(null);
        setMessages([]);
      }
    } catch (error) { alert("Ошибка удаления"); }
  };

  const deleteChar = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Удалить персонажа? Все его чаты также будут удалены.")) return;
    try {
      await fetch(`${API_URL}/characters/${id}`, { method: 'DELETE' });
      fetchCharacters(); 
      fetchConversations();
      if (selectedCharId === id) setSelectedCharId(null);
      if (viewingChar && viewingChar.id === id) setViewingChar(null);
      if (conversationId) {
        setConversationId(null); 
        setMessages([]);
      }
    } catch (error) { alert("Ошибка удаления"); }
  };

  const handleCreateCharacter = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/characters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setIsModalOpen(false);
        setFormData({ name: "", description: "", personality: "", scenario: "", first_message: "" });
        fetchCharacters();
      }
    } catch (error) { alert("Ошибка при создании"); }
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    
    e.target.style.height = 'auto'; 
    e.target.style.height = `${e.target.scrollHeight}px`;
  };


  // --- СТРИМИНГ ---
  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage, { role: "assistant", content: "" }]);
    
    setInput("");
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
    
    setIsLoading(true);

    try {
      const payload = { message: userMessage.content, conversation_id: conversationId, character_id: selectedCharId };
      const res = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Ошибка сервера");

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const textChunk = decoder.decode(value, { stream: true });
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          newMessages[lastIndex] = { ...newMessages[lastIndex], content: newMessages[lastIndex].content + textChunk };
          return newMessages;
        });
      }

      if (!conversationId) {
        fetchConversations(); 
        const convsRes = await fetch(`${API_URL}/conversations`);
        const convs = await convsRes.json();
        if (convs.length > 0) {
          setConversationId(convs[0].id);
          setSelectedCharId(null);
        }
      }
    } catch (e) { alert(e.message); } finally { setIsLoading(false); }
  };

  return (
    <div className="app-container">
      {/* ЛЕВАЯ ПАНЕЛЬ */}
      <div className="sidebar">
        <div className="sidebar-section">
          <div className="sidebar-header-row">
            <h3>🎭 Персонажи</h3>
            <button className="add-btn" onClick={() => setIsModalOpen(true)}>+</button>
          </div>
          {characters.map(char => (
            <div 
              key={char.id} 
              className={`item-row ${(viewingChar?.id === char.id || selectedCharId === char.id) ? 'active' : ''}`}
              onClick={() => handleCharClick(char)}
            >
              <span className="item-name">{char.name}</span>
              <button className="delete-icon-btn" onClick={(e) => deleteChar(e, char.id)}>✕</button>
            </div>
          ))}
        </div>

        <div className="sidebar-section">
          <h3>💬 История</h3>
          {conversations.map(conv => (
            <div 
              key={conv.id} 
              className={`item-row ${conversationId === conv.id ? 'active' : ''}`}
              onClick={() => loadMessages(conv.id)}
            >
              <span className="item-name">{conv.title}</span>
              <button className="delete-icon-btn" onClick={(e) => deleteChat(e, conv.id)}>✕</button>
            </div>
          ))}
        </div>
      </div>

      {/* ПРАВАЯ ПАНЕЛЬ */}
      <div className="chat-area">
        {viewingChar ? (
          /* --- ЭКРАН КАРТОЧКИ ПЕРСОНАЖА --- */
          <div className="character-profile">
            {isEditingProfile ? (
              /* РЕЖИМ РЕДАКТИРОВАНИЯ */
              <form onSubmit={handleUpdateCharacter} className="profile-edit-form">
                <h2>Редактирование: {viewingChar.name}</h2>
                
                <label>Имя</label>
                <textarea 
                  name="name" 
                  value={editFormData.name || ""} 
                  onChange={handleEditChange} 
                  ref={(el) => {
                    if (el) {
                      el.style.height = 'auto';
                      el.style.height = `${el.scrollHeight}px`;
                    }
                  }}
                />

                <label>Описание</label>
                <textarea 
                  name="description" 
                  value={editFormData.description || ""} 
                  onChange={handleEditChange} 
                  ref={(el) => {
                    if (el) {
                      el.style.height = 'auto';
                      el.style.height = `${el.scrollHeight}px`;
                    }
                  }}
                />

                <label>Характер</label>
                <textarea 
                  name="personality" 
                  value={editFormData.personality || ""} 
                  onChange={handleEditChange} 
                  ref={(el) => {
                    if (el) {
                      el.style.height = 'auto';
                      el.style.height = `${el.scrollHeight}px`;
                    }
                  }}
                />

                <label>Сценарий</label>
                <textarea 
                  name="scenario" 
                  value={editFormData.scenario || ""} 
                  onChange={handleEditChange} 
                  ref={(el) => {
                    if (el) {
                      el.style.height = 'auto';
                      el.style.height = `${el.scrollHeight}px`;
                    }
                  }}
                />

                <label>Первое сообщение</label>
                <textarea 
                  name="first_message" 
                  value={editFormData.first_message || ""} 
                  onChange={handleEditChange} 
                  ref={(el) => {
                    if (el) {
                      el.style.height = 'auto';
                      el.style.height = `${el.scrollHeight}px`;
                    }
                  }}
                />

                <div className="modal-actions">
                  <button type="button" onClick={() => setIsEditingProfile(false)} className="cancel-btn">Отмена</button>
                  <button type="submit" className="submit-btn">Сохранить</button>
                </div>
              </form>
            ) : (
              /* РЕЖИМ ПРОСМОТРА */
              <>
                <div className="profile-header-row">
                  <h1>{viewingChar.name}</h1>
                  <button className="edit-btn" onClick={startEditingProfile}>✏️ Редактировать</button>
                </div>
                
                <div className="profile-field">
                  <label>📝 Описание</label>
                  <p>{viewingChar.description || "Не указано"}</p>
                </div>

                <div className="profile-field">
                  <label>🧠 Характер</label>
                  <p>{viewingChar.personality || "Не указано"}</p>
                </div>

                <div className="profile-field">
                  <label>🎬 Сценарий</label>
                  <p>{viewingChar.scenario || "Не указано"}</p>
                </div>

                <div className="profile-field">
                  <label>💬 Первое сообщение</label>
                  <div className="first-msg-preview">
                    {viewingChar.first_message ? (
                      <ReactMarkdown remarkPlugins={[remarkBreaks]}>
                        {viewingChar.first_message}
                      </ReactMarkdown>
                    ) : (
                      "Нет"
                    )}
                  </div>
                </div>

                <button className="start-chat-btn" onClick={startChatWithChar}>
                  Начать диалог
                </button>
              </>
            )}
          </div>
        ) : (
          /* --- ЭКРАН ЧАТА --- */
          <>
            <div className="chat-header">
              {selectedCharId 
                ? `Новый чат: ${characters.find(c => c.id === selectedCharId)?.name}` 
                : conversationId ? `Чат` : "Выберите персонажа слева"}
            </div>

            <div className="messages-list">
              {messages.length === 0 && <p className="empty-msg">Напишите первое сообщение...</p>}

              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="msg-content">
                  <ReactMarkdown remarkPlugins={[remarkBreaks]}>
                    {msg.content}
                  </ReactMarkdown>
                  </div>
                </div>
              ))}
              {isLoading && <div className="message assistant"><div className="msg-content">Печатает...</div></div>}
              <div ref={messagesEndRef} />
            </div>

                        <div className="input-area">
              <textarea 
                ref={inputRef}
                value={input} 
                onChange={(e) => {
                  setInput(e.target.value);
                  // Авто-ресайз прямо при вводе
                  e.target.style.height = 'auto';
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
                }}
                onKeyDown={(e) => {
                  // Если нажат Enter БЕЗ Shift — отправляем
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault(); // Запрещаем стандартный перенос строки
                    sendMessage();
                  }
                  // Если Shift+Enter — ничего не делаем, сработает стандартный перенос
                }}
                placeholder="Введите сообщение... (Shift+Enter для новой строки)"
                disabled={!selectedCharId && !conversationId}
                rows={1}
              />
              <button onClick={sendMessage} disabled={isLoading || (!selectedCharId && !conversationId)}>Отправить</button>
            </div>
          </>
        )}
      </div>

      {/* МОДАЛЬНОЕ ОКНО СОЗДАНИЯ */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Создать персонажа</h2>
            <form onSubmit={handleCreateCharacter} className="char-form">
              <label>Имя *</label>
              <input name="name" value={formData.name} onChange={handleInputChange} required />
              <label>Описание</label>
              <textarea name="description" value={formData.description} onChange={handleInputChange} />
              <label>Характер</label>
              <textarea name="personality" value={formData.personality} onChange={handleInputChange} />
              <label>Сценарий</label>
              <textarea name="scenario" value={formData.scenario} onChange={handleInputChange} />
              <label>Первое сообщение</label>
              <textarea name="first_message" value={formData.first_message} onChange={handleInputChange} />
              <div className="modal-actions">
                <button type="button" onClick={() => setIsModalOpen(false)} className="cancel-btn">Отмена</button>
                <button type="submit" className="submit-btn">Создать</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;