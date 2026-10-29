import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import './App.css';
import { apiFetch } from './api';

function App() {
  const [characters, setCharacters] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);

  const [selectedCharId, setSelectedCharId] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [viewingChar, setViewingChar] = useState(null);

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

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

  const fetchCharacters = async () => {
    try {
      const res = await apiFetch("/characters");
      const data = await res.json();
      setCharacters(data);
    } catch (e) { console.error(e); }
  };

  const fetchConversations = async () => {
    try {
      const res = await apiFetch("/conversations");
      const data = await res.json();
      setConversations(data);
    } catch (e) { console.error(e); }
  };

  const loadMessages = async (convId) => {
    try {
      const res = await apiFetch(`/conversations/${convId}/messages`);
      const data = await res.json();
      setMessages(data);
      setConversationId(convId);
      setSelectedCharId(null);
      setViewingChar(null);
      setIsEditingProfile(false);
    } catch (e) { console.error(e); }
  };

  const handleCharClick = (char) => {
    setViewingChar(char);
    setConversationId(null);
    setSelectedCharId(null);
    setMessages([]);
    setIsEditingProfile(false);
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

  const startEditingProfile = () => {
    setEditFormData(viewingChar);
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
      const res = await apiFetch(`/characters/${viewingChar.id}`, {
        method: 'PATCH',
        body: JSON.stringify(editFormData)
      });

      if (res.ok) {
        const updatedChar = await res.json();
        setViewingChar(updatedChar);
        setIsEditingProfile(false);
        fetchCharacters();
      }
    } catch (error) {
      alert("Ошибка при обновлении персонажа");
    }
  };

  const deleteChat = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Удалить этот чат?")) return;
    try {
      await apiFetch(`/conversations/${id}`, { method: 'DELETE' });
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
      await apiFetch(`/characters/${id}`, { method: 'DELETE' });
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
      const res = await apiFetch("/characters", {
        method: 'POST',
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
      const payload = {
        message: userMessage.content,
        conversation_id: conversationId,
        character_id: selectedCharId
      };
      const res = await apiFetch("/chat", {
        method: 'POST',
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
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            content: newMessages[lastIndex].content + textChunk
          };
          return newMessages;
        });
      }

      if (!conversationId) {
        fetchConversations();
      }
    } catch (error) {
      console.error(error);
      alert("Ошибка при отправке сообщения");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div style={{ padding: "10px 16px" }}>
          <a href="/profile" className="profile-link">Профиль</a>
        </div>

        <div className="sidebar-section">
          <h3>Персонажи</h3>
          <button className="new-char-btn" onClick={() => setIsModalOpen(true)}>+ Создать</button>
          {characters.map((char) => (
            <div
              key={char.id}
              className={`char-item ${viewingChar?.id === char.id ? "active" : ""}`}
              onClick={() => handleCharClick(char)}
            >
              <span>{char.name}</span>
              <button className="delete-btn" onClick={(e) => deleteChar(e, char.id)}>×</button>
            </div>
          ))}
        </div>

        <div className="sidebar-section">
          <h3>История</h3>
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conv-item ${conversationId === conv.id ? "active" : ""}`}
              onClick={() => loadMessages(conv.id)}
            >
              <span>{conv.title}</span>
              <button className="delete-btn" onClick={(e) => deleteChat(e, conv.id)}>×</button>
            </div>
          ))}
        </div>
      </div>

      {/* Main area */}
      <div className="main">
        {viewingChar && !isEditingProfile && (
          <div className="char-profile">
            <h2>{viewingChar.name}</h2>
            <p><b>Описание:</b> {viewingChar.description}</p>
            <p><b>Характер:</b> {viewingChar.personality}</p>
            <p><b>Сценарий:</b> {viewingChar.scenario}</p>
            <button onClick={startChatWithChar}>Начать чат</button>
            <button onClick={startEditingProfile}>Редактировать</button>
          </div>
        )}

        {viewingChar && isEditingProfile && (
          <form className="edit-form" onSubmit={handleUpdateCharacter}>
            <h3>Редактирование</h3>
            <textarea name="name" value={editFormData.name || ""} onChange={handleEditChange} placeholder="Имя" />
            <textarea name="description" value={editFormData.description || ""} onChange={handleEditChange} placeholder="Описание" />
            <textarea name="personality" value={editFormData.personality || ""} onChange={handleEditChange} placeholder="Характер" />
            <textarea name="scenario" value={editFormData.scenario || ""} onChange={handleEditChange} placeholder="Сценарий" />
            <textarea name="first_message" value={editFormData.first_message || ""} onChange={handleEditChange} placeholder="Первое сообщение" />
            <button type="submit">Сохранить</button>
            <button type="button" onClick={() => setIsEditingProfile(false)}>Отмена</button>
          </form>
        )}

        {!viewingChar && (
          <div className="chat-area">
            <div className="messages">
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <ReactMarkdown remarkPlugins={[remarkBreaks]}>{msg.content}</ReactMarkdown>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="input-area">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = e.target.scrollHeight + "px";
                }}
                onKeyDown={handleKeyDown}
                placeholder="Напишите сообщение..."
                disabled={isLoading}
              />
              <button onClick={sendMessage} disabled={isLoading}>
                {isLoading ? "..." : "Отправить"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal создания персонажа */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Новый персонаж</h3>
            <form onSubmit={handleCreateCharacter}>
              <input name="name" placeholder="Имя" value={formData.name} onChange={handleInputChange} required />
              <textarea name="description" placeholder="Описание" value={formData.description} onChange={handleInputChange} />
              <textarea name="personality" placeholder="Характер" value={formData.personality} onChange={handleInputChange} />
              <textarea name="scenario" placeholder="Сценарий" value={formData.scenario} onChange={handleInputChange} />
              <textarea name="first_message" placeholder="Первое сообщение" value={formData.first_message} onChange={handleInputChange} />
              <button type="submit">Создать</button>
              <button type="button" onClick={() => setIsModalOpen(false)}>Отмена</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;