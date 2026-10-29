import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import "./css/admin.css";

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newRole, setNewRole] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/users/");
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      } else {
        setMessage("Нет доступа или ошибка загрузки");
      }
    } catch (e) {
      setMessage("Ошибка сети");
    }
    setLoading(false);
  };

  const handleRoleChange = async () => {
    if (!selectedUser || !newRole) return;
    const res = await apiFetch("/users/role", {
      method: "PATCH",
      body: JSON.stringify({ username: selectedUser.username, role: newRole }),
    });
    if (res.ok) {
      setMessage("Роль обновлена");
      loadUsers();
      setSelectedUser(null);
    } else {
      setMessage("Не удалось обновить роль");
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-card">
        <h2>Панель администратора</h2>

        {message && <p className="admin-message">{message}</p>}

        <div className="admin-section">
          <h3>Пользователи</h3>
          {loading ? (
            <p>Загрузка...</p>
          ) : users.length === 0 ? (
            <p>Пользователей нет</p>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Ник</th>
                  <th>Email</th>
                  <th>Роль</th>
                  <th>Баланс</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.email}</td>
                    <td className="role">{u.role}</td>
                    <td>{u.balance}</td>
                    <td>
                      <button
                        className="role-btn"
                        onClick={() => {
                          setSelectedUser(u);
                          setNewRole(u.role);
                        }}
                      >
                        Роль
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {selectedUser && (
          <div className="role-editor">
            <h4>Смена роли: {selectedUser.username}</h4>
            <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
              <option value="guest">guest</option>
              <option value="wanderer">wanderer</option>
              <option value="expert">expert</option>
              <option value="legend">legend</option>
              <option value="admin">admin</option>
            </select>
            <button onClick={handleRoleChange}>Сохранить</button>
            <button className="cancel" onClick={() => setSelectedUser(null)}>
              Отмена
            </button>
          </div>
        )}

        <a href="/" className="back-link">← Назад в чат</a>
      </div>
    </div>
  );
}