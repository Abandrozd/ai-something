from app.security import hash_password, verify_password


def test_hash_password_not_equal_to_original():
    password = "mysecret"
    hashed = hash_password(password)
    assert hashed != password


def test_verify_correct_password():
    password = "mysecret"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_wrong_password():
    hashed = hash_password("mysecret")
    assert verify_password("wrongpassword", hashed) is False