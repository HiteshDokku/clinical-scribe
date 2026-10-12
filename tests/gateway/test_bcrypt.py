import bcrypt

def test_bcrypt_round_trip():
    # Simulate migration's hashing
    password = "secret_password"
    
    # Generate hash exactly as the migration does
    salt = bcrypt.gensalt()
    hash_str = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    assert isinstance(hash_str, str)
    assert hash_str.startswith("$2b$") or hash_str.startswith("$2a$")
    
    # Simulate gateway login verification exactly as login endpoint does
    is_valid = bcrypt.checkpw(password.encode('utf-8'), hash_str.encode('utf-8'))
    assert is_valid is True
    
    # Verify wrong password fails
    is_valid_wrong = bcrypt.checkpw("wrong_password".encode('utf-8'), hash_str.encode('utf-8'))
    assert is_valid_wrong is False
