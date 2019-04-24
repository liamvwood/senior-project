from collections import OrderedDict

import binascii

import Cryptodome
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import DSS

class Transaction:

    def __init__(self, sender_address, sender_private_key, recipient_address, value):
        self.sender_address = sender_address
        self.sender_private_key = sender_private_key
        self.recipient_address = recipient_address
        self.value = value

    def __getattr__(self, attr):
        return self.data[attr]

    def to_dict(self):
        return OrderedDict({'sender_address': self.sender_address,
                            'recipient_address': self.recipient_address,
                            'value': self.value})

    def sign_transaction(self):
        """
        Sign transaction with private key
        """
        private_key = ECC.import_key(binascii.unhexlify(self.sender_private_key))
        signer = DSS.new(private_key, 'fips-186-3')
        h = SHA256.new(str(self.to_dict()).encode('utf8'))
        return binascii.hexlify(signer.sign(h)).decode('ascii')

class Investment(Transaction):

    def __init__(self, sender_address, sender_private_key, recipient_address, value, url):
        self.url = url
        Transaction.__init__(self, sender_address, sender_private_key, recipient_address, value)

    def to_dict(self):
        return OrderedDict({'sender_address': self.sender_address,
                            'recipient_address': self.recipient_address,
                            'value': self.value,
                            'url':self.url})
