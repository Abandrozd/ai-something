import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, clearTokens } from "../api";

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
    } catch (e) {
      // игнорируем ошибку
    }
    clearTokens();
    navigate("/login");
  };

  if (error) return <p>{error}</p>;
  if (!user) return <p>Загрузка...</p>;

  return (
    <div style={{ maxWidth: 500, margin: "50px auto" }}>
      <h2>Профиль</h2>
      <p><b>Username:</b> {user.username}</p>
      <p><b>Email:</b> {user.email}</p>
      <p><b>Роль:</b> {user.role}</p>
      <p><b>Баланс:</b> {user.balance}</p>
      <br />
      <button onClick={handleLogout}>Выйти</button>
      <br /><br />
      <a href="/">Вернуться в чат</a>
    </div>
  );
}