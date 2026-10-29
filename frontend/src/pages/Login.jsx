import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { setTokens } from "../api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const formData = new FormData();
    formData.append("username", username);
    formData.append("password", password);

    try {
      const res = await fetch("http://127.0.0.1:8000/auth/login", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Неверный логин или пароль");
      }

      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "100px auto" }}>
      <h2>Вход</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <br />
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <br />
        <button type="submit">Войти</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <p>
        Нет аккаунта? <a href="/register">Зарегистрироваться</a>
      </p>
    </div>
  );
}