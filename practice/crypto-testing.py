from Cryptodome.PublicKey import RSA
from Cryptodome.Random import get_random_bytes
from Cryptodome.Cipher import AES, PKCS1_OAEP

# generates a key object somewhere in memory
# generates a private key (key.export_key()) and public key (key.public_key.export_key())
key = RSA.generate(2048)

# gets the key from memory and stores in as a string
private_key = key.export_key()
print(f'Private key: {key.size_in_bytes()}')
file_out = open("private.pem", "wb")
file_out.write(private_key)

# gets the public key from memory
public_key = key.publickey().export_key()
print(f'Public key: {key.publickey().size_in_bytes()}')
file_out = open("receiver.pem", "wb")
file_out.write(public_key)

# some message encoded into bytes
data = "I met aliens in UFO. Here is the map.".encode("utf-8")
file_out = open("encrypted_data.bin", "wb")

# read some public key and create a public_key object
recipient_key = RSA.import_key(open("receiver.pem").read())

session_key = get_random_bytes(16)

# Encrypt the session key with the public RSA key
cipher_rsa = PKCS1_OAEP.new(recipient_key)
enc_session_key = cipher_rsa.encrypt(session_key)

# Encrypt the data with the AES session key
cipher_aes = AES.new(session_key, AES.MODE_EAX)
ciphertext, tag = cipher_aes.encrypt_and_digest(data)
[ file_out.write(x) for x in (enc_session_key, cipher_aes.nonce, tag, ciphertext) ]