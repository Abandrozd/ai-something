import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await fetch("http://127.0.0.1:8000/users/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, role: "guest" }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Ошибка регистрации");
      }

      navigate("/login");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "100px auto" }}>
      <h2>Регистрация</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <br />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
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
        <button type="submit">Зарегистрироваться</button>
      </form>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <p>
        Уже есть аккаунт? <a href="/login">Войти</a>
      </p>
    </div>
  );
}