// Keep these equal to backend/app/request_limits.py.
export const MAX_PASSWORD_LENGTH = 256;
export const MAX_MESSAGE_LENGTH = 4000;

export function textLength(value) {
  return Array.from(value ?? "").length;
}

export function passwordTooLong(password) {
  return textLength(password) > MAX_PASSWORD_LENGTH;
}

export function messageTooLong(message) {
  return textLength(message) > MAX_MESSAGE_LENGTH;
}

export function passwordLengthMessage() {
  return `Пароль должен быть не длиннее ${MAX_PASSWORD_LENGTH} символов`;
}

export function messageLengthMessage() {
  return `Сообщение должно быть не длиннее ${MAX_MESSAGE_LENGTH} символов`;
}

export function readErrorDetail(data, fallback) {
  const detail = data && data.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item.msg === "string" ? item.msg : ""))
      .filter(Boolean);
    if (messages.length > 0) return messages.join(" ");
  }
  return fallback;
}
