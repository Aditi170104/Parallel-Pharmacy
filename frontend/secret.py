import secrets

# Generate a random secret key
secret_key = secrets.token_hex(16)  # 16 bytes for a 32-character hexadecimal string

print("Generated Secret Key:", secret_key)
