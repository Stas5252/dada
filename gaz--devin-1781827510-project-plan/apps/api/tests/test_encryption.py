from app.encryption import decrypt_token, encrypt_token

def test_encryption_roundtrip():
    secret = "my-super-secret-key-123!"
    plain_token = "123456789:ABCDEF-abcdef-123456"
    
    cipher_text = encrypt_token(plain_token, secret)
    assert cipher_text != plain_token
    assert len(cipher_text) > len(plain_token)
    
    decrypted = decrypt_token(cipher_text, secret)
    assert decrypted == plain_token

def test_encryption_invalid_secret():
    secret1 = "secret-1"
    secret2 = "secret-2"
    plain_token = "hello-world"
    
    cipher_text = encrypt_token(plain_token, secret1)
    
    # Decrypting with wrong secret should fail gracefully
    decrypted = decrypt_token(cipher_text, secret2)
    assert decrypted is None

def test_encryption_invalid_token():
    secret = "secret-1"
    assert decrypt_token("not-a-valid-token", secret) is None

def test_encryption_empty_strings():
    secret = "secret"
    assert encrypt_token("", secret) == ""
    assert decrypt_token("", secret) is None
