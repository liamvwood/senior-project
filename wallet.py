import binascii

import Cryptodome
import Cryptodome.Random
from Cryptodome.Hash import SHA256, RIPEMD160
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import DSS


class Wallet(object):
    """
    A wallet is a private/public key pair
    """

    def __init__(self, private_key=None):
        random_gen = Cryptodome.Random.new().read

        if not private_key:
            self._private_key = ECC.generate(curve='P-256')
        else:
            self._private_key = ECC.import_key(binascii.unhexlify(private_key))

        self._public_key = self._private_key.public_key()
        self._signer = DSS.new(self._private_key, 'fips-186-3')

    @property
    def address(self):
        """We take a shortcut and say address is public key"""

        # Run SHA256 for the public key
        sha256_bpk = SHA256.new(binascii.hexlify(
            self._public_key.export_key(format='DER')))
        sha256_bpk_digest = sha256_bpk.digest()

        # Run ripemd160 for the SHA256
        ripemd160_bpk = RIPEMD160.new(sha256_bpk_digest)
        ripemd160_bpk_digest = ripemd160_bpk.digest()
        ripemd160_bpk_hex = binascii.hexlify(ripemd160_bpk_digest)

        # Add network byte
        network_byte = b'00'
        network_bitcoin_public_key = network_byte + ripemd160_bpk_hex

        sha256_nbpk = SHA256.new(network_bitcoin_public_key)
        sha256_nbpk_digest = sha256_nbpk.digest()
        sha256_2_nbpk = SHA256.new(sha256_nbpk_digest)
        sha256_2_nbpk_digest = sha256_2_nbpk.digest()

        sha256_2_hex = binascii.hexlify(sha256_2_nbpk_digest)
        checksum = sha256_2_hex[:8]

        address_hex = (network_bitcoin_public_key + checksum).decode('utf-8')
        address = base58(address_hex)

        return address

    def public_key(self):
        return binascii.hexlify(self._public_key.export_key(format='DER')).decode('ascii')

    def sign(self, message):
        """
        Sign a message with this wallet
        """
        h = SHA256.new(message.encode('utf8'))
        return binascii.hexlify(self._signer.sign(h)).decode('ascii')


def base58(address_hex):
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    b58_string = ''
    # Get the number of leading zeros and convert hex to decimal
    leading_zeros = len(address_hex) - len(address_hex.lstrip('0'))
    # Convert hex to decimal
    address_int = int(address_hex, 16)
    # Append digits to the start of string
    while address_int > 0:
        digit = address_int % 58
        digit_char = alphabet[digit]
        b58_string = digit_char + b58_string
        address_int //= 58
    # Add '1' for each 2 leading zeros
    ones = leading_zeros // 2
    for one in range(ones):
        b58_string = '1' + b58_string
    return b58_string


def verify_signature(wallet_address, message, signature):
    """
    Check that the provided `signature` corresponds to `message`
    signed by the wallet at `wallet_address`
    """
    print('DEBUG1')
    pubkey = ECC.import_key(binascii.unhexlify(wallet_address))
    verifier = DSS.new(pubkey, 'fips-186-3')
    h = SHA256.new(message.encode('utf8'))
    try:
        verifier.verify(h, binascii.unhexlify(signature))
        return True
    except ValueError:
        print('this signature is NOT authentic')
        return False