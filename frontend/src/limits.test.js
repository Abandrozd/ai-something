import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_MESSAGE_LENGTH,
  MAX_PASSWORD_LENGTH,
  messageLengthMessage,
  messageTooLong,
  passwordLengthMessage,
  passwordTooLong,
  readErrorDetail,
} from "./limits.js";

test("password cap is 256 characters and the error names it", () => {
  assert.equal(MAX_PASSWORD_LENGTH, 256);
  assert.equal(passwordTooLong("a".repeat(256)), false);
  assert.equal(passwordTooLong("я".repeat(256)), false);
  assert.equal(passwordTooLong("я".repeat(257)), true);
  assert.equal(passwordTooLong("🙂".repeat(257)), true);
  assert.match(passwordLengthMessage(), /256/);
});

test("api validation errors keep the limit text", () => {
  const data = {
    detail: [{ msg: "String should have at most 4000 characters" }],
  };
  assert.equal(
    readErrorDetail(data, "fallback"),
    "String should have at most 4000 characters",
  );
  assert.equal(readErrorDetail({ detail: "Слишком много попыток" }, "fallback"), "Слишком много попыток");
  assert.equal(readErrorDetail(null, "fallback"), "fallback");
});

test("chat message cap is 4000 characters and the error names it", () => {
  assert.equal(MAX_MESSAGE_LENGTH, 4000);
  assert.equal(messageTooLong("a".repeat(4000)), false);
  assert.equal(messageTooLong("a".repeat(4001)), true);
  assert.match(messageLengthMessage(), /4000/);
});
