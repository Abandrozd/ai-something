import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, clearTokens } from "../api";
import "./css/Profile.css";

export default function Profile() {
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");
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
    // позже сюда можно поставить переход на страницу оплаты
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

        <button className="profile-logout" onClick={handleLogout}>
          Выйти
        </button>

        <a href="/" className="profile-back">
          Вернуться в чат
        </a>
      </div>
    </div>
  );
}