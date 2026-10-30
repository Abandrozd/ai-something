import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, clearTokens } from "../api";
import "./css/Profile.css";

export default function Profile() {
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch("/users/me")
      .then((res) => res.json())
      .then(setUser)
      .catch(() => setError("Не удалось загрузить профиль"));
  }, []);

  const handleLogout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch (e) {}
    clearTokens();
    navigate("/login");
  };

  const handleTopUp = () => {
    alert("Пополнение баланса будет доступно позже");
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordMessage("");

    try {
      const res = await apiFetch("/users/change-password", {
        method: "POST",
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      if (res.ok) {
        setPasswordMessage("Пароль успешно изменён");
        setOldPassword("");
        setNewPassword("");
      } else {
        const data = await res.json();
        setPasswordMessage(data.detail || "Ошибка при смене пароля");
      }
    } catch (e) {
      setPasswordMessage("Ошибка сети");
    }
  };

  if (error) return <div className="profile-container"><p className="profile-error">{error}</p></div>;
  if (!user) return <div className="profile-container"><p>Загрузка...</p></div>;

  return (
    <div className="profile-container">
      <div className="profile-card">
        <h2 className="profile-title">Профиль</h2>

        <div className="profile-info">
          <div className="profile-row">
            <span className="profile-label">Никнейм</span>
            <span className="profile-value">{user.username}</span>
          </div>

          <div className="profile-row">
            <span className="profile-label">Email</span>
            <span className="profile-value">{user.email}</span>
          </div>

          <div className="profile-row">
            <span className="profile-label">Статус</span>
            <span className="profile-value profile-role">{user.role}</span>
          </div>

          <div className="profile-row">
            <span className="profile-label">Баланс</span>
            <span className="profile-value profile-balance">{user.balance} ₽</span>
          </div>
        </div>

        <button className="profile-topup" onClick={handleTopUp}>
          Пополнить
        </button>

        {/* Смена пароля */}
        <div className="password-section">
          <h3>Смена пароля</h3>
          <form onSubmit={handleChangePassword}>
            <input
              type="password"
              placeholder="Текущий пароль"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Новый пароль"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <button type="submit">Сменить пароль</button>
          </form>
          {passwordMessage && (
            <p className={passwordMessage.includes("успешно") ? "success" : "error"}>
              {passwordMessage}
            </p>
          )}
        </div>

        <button className="profile-logout" onClick={handleLogout}>
          Выйти
        </button>

        {user.role === "admin" && (
          <a href="/admin" className="profile-back" style={{ display: "block", marginTop: "10px" }}>
            Админ-панель
          </a>
        )}

        <a href="/" className="profile-back">
          Вернуться в чат
        </a>
      </div>
    </div>
  );
}