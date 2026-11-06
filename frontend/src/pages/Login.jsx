import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_URL, clearStoredTokens } from "../api";
import { passwordLengthMessage, passwordTooLong, readErrorDetail } from "../limits";
import "./css/Login.css";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (passwordTooLong(password)) {
      setError(passwordLengthMessage());
      return;
    }

    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        credentials: "include",
        body: formData,
      });

      if (res.status === 429 || res.status === 422) {
        const data = await res.json().catch(() => null);
        const fallback = res.status === 429
          ? "Слишком много попыток. Повторите позже."
          : passwordLengthMessage();
        throw new Error(readErrorDetail(data, fallback));
      }

      if (!res.ok) throw new Error("Неверный логин или пароль");

      clearStoredTokens();
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h2 className="login-title">Вход</h2>
        <p className="login-subtitle">Добро пожаловать обратно</p>

        <form onSubmit={handleSubmit} className="login-form">
          <input
            className="login-input"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            className="login-input"
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="login-button" type="submit">
            Войти
          </button>
        </form>

        {error && <p className="login-error">{error}</p>}

        <p className="login-footer">
          Нет аккаунта? <a href="/register">Зарегистрироваться</a>
        </p>
      </div>
    </div>
  );
}