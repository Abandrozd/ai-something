import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import "./css/admin.css";

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newRole, setNewRole] = useState("");
  const [balanceUser, setBalanceUser] = useState(null);
  const [amount, setAmount] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const [limits, setLimits] = useState({
    guest: 5,
    wanderer: 10,
    expert: 15,
    legend: 20,
    admin: 1000000,
  });
  const [limitsLoaded, setLimitsLoaded] = useState(false);

  useEffect(() => {
    loadUsers();
    loadLimits();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/users/");
      if (res.ok) {
        setUsers(await res.json());
      } else {
        setMessage("Нет доступа или ошибка загрузки");
      }
    } catch (e) {
      setMessage("Ошибка сети");
    }
    setLoading(false);
  };

  const loadLimits = async () => {
    try {
      const res = await apiFetch("/users/limits");
      if (res.ok) {
        setLimits(await res.json());
        setLimitsLoaded(true);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const saveLimits = async () => {
    const res = await apiFetch("/users/limits", {
      method: "PUT",
      body: JSON.stringify(limits),
    });
    if (res.ok) {
      setMessage("Лимиты сохранены");
    } else {
      setMessage("Не удалось сохранить лимиты");
    }
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

  const handleBalance = async () => {
    if (!balanceUser || !amount) return;
    const res = await apiFetch("/users/balance", {
      method: "PATCH",
      body: JSON.stringify({
        username: balanceUser.username,
        amount: parseFloat(amount),
      }),
    });
    if (res.ok) {
      setMessage("Баланс обновлён");
      loadUsers();
      setBalanceUser(null);
      setAmount("");
    } else {
      setMessage("Не удалось обновить баланс");
    }
  };

  const toggleStatus = async (user) => {
    const res = await apiFetch("/users/status", {
      method: "PATCH",
      body: JSON.stringify({
        username: user.username,
        is_active: !user.is_active,
      }),
    });
    if (res.ok) {
      setMessage(user.is_active ? "Пользователь заблокирован" : "Пользователь разблокирован");
      loadUsers();
    } else {
      setMessage("Не удалось изменить статус");
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-card">
        <h2>Панель администратора</h2>

        {message && <p className="admin-message">{message}</p>}

        {/* Пользователи */}
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
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.username}</td>
                    <td>{u.email}</td>
                    <td className="role">{u.role}</td>
                    <td>{u.balance}</td>
                    <td>{u.is_active ? "Активен" : "Заблокирован"}</td>
                    <td className="actions">
                      <button
                        className="role-btn"
                        onClick={() => {
                          setSelectedUser(u);
                          setNewRole(u.role);
                        }}
                      >
                        Роль
                      </button>
                      <button className="balance-btn" onClick={() => setBalanceUser(u)}>
                        Баланс
                      </button>
                      <button
                        className={u.is_active ? "block-btn" : "unblock-btn"}
                        onClick={() => toggleStatus(u)}
                      >
                        {u.is_active ? "Блок" : "Разблок"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Лимиты */}
        <div className="admin-section">
          <h3>Лимиты сообщений на диалог</h3>
          {limitsLoaded ? (
            <div className="limits-form">
              {Object.entries(limits).map(([role, value]) => (
                <div key={role} className="limit-row">
                  <label>{role}</label>
                  <input
                    type="number"
                    value={value}
                    onChange={(e) =>
                      setLimits({ ...limits, [role]: parseInt(e.target.value) || 0 })
                    }
                  />
                </div>
              ))}
              <button onClick={saveLimits}>Сохранить лимиты</button>
            </div>
          ) : (
            <p>Загрузка лимитов...</p>
          )}
        </div>

        {/* Модалки */}
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

        {balanceUser && (
          <div className="role-editor">
            <h4>Баланс: {balanceUser.username} (сейчас {balanceUser.balance})</h4>
            <input
              type="number"
              placeholder="Сумма (+ или -)"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <button onClick={handleBalance}>Начислить</button>
            <button className="cancel" onClick={() => setBalanceUser(null)}>
              Отмена
            </button>
          </div>
        )}

        <a href="/" className="back-link">← Назад в чат</a>
      </div>
    </div>
  );
}