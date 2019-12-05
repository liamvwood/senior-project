from collections import OrderedDict

import binascii
import json
import hashlib
import logging
import numpy as np
import Cryptodome
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import DSS

from wallet import Wallet, verify_signature

class TransactionInput(object):
    """
    An input for a transaction. This points to an output of another transaction
    """

    def __init__(self, transaction, output_index):
        self.transaction = transaction
        self.output_index = output_index
        assert 0 <= self.output_index < len(transaction.outputs)

    def to_dict(self):
        d = OrderedDict({
            'transaction': self.transaction.hash(),
            'output_index': self.output_index
        })
        return d

    @property
    def parent_output(self):
        return self.transaction.outputs[self.output_index]


class TransactionOutput(object):
    """
    An output for a transaction. This specifies an amount and a recipient (wallet)
    """

    def __init__(self, recipient_address, amount):
        self.recipient = recipient_address
        self.amount = amount

    def to_dict(self):
        d = OrderedDict({
            'recipient_address': self.recipient,
            'amount': self.amount
        })
        return d


def compute_fee(inputs, outputs):
    """
    Compute the transaction fee by computing the difference between total input and total output
    """
    
    total_in = sum(
        i.transaction.outputs[i.output_index].amount for i in inputs)
    total_out = sum(o.amount for o in outputs)
    assert total_out <= total_in, "Invalid transaction with out(%f) > in(%f)" % (
        total_out, total_in)
    return total_in - total_out


class Transaction(object):
    def __init__(self, wallet, inputs, outputs):
        """
        Create a transaction spending money from the provided wallet
        """
        self.inputs = inputs
        self.outputs = outputs
        self.fee = compute_fee(inputs, outputs)
        self.signature = wallet.sign(json.dumps(
            self.to_dict(include_signature=False)))

    def to_dict(self, include_signature=True):
        d = OrderedDict({
            "inputs": list(map(TransactionInput.to_dict, self.inputs)),
            "outputs": list(map(TransactionOutput.to_dict, self.outputs)),
            "fee": self.fee
        })

        if include_signature:
            d["signature"] = self.signature

        return d

    def hash(self):
        return hashlib.sha256(json.dumps(self.to_dict()).encode()).hexdigest()


class GenesisTransaction(Transaction):
    """
    This is the first transaction which is a special transaction
    with no input and 25 bitcoins output
    """

    def __init__(self, recipient_address, amount=25):
        self.inputs = []
        self.outputs = [
            TransactionOutput(recipient_address, amount)
        ]
        self.fee = 0
        self.signature = 'genesis'

    def to_dict(self, include_signature=False):
        # TODO: Instead, should sign genesis transaction will well-known public key ?
        assert not include_signature, "Cannot include signature of genesis transaction"
        return super().to_dict(include_signature=False)



def compute_balance(wallet_address, transactions):
    """
    Given an address and a list of transactions, computes the wallet balance of the address
    """
    balance = 0
    for t in transactions:
        # Subtract all the money that the address sent out
        for txin in t.inputs:
            if txin.parent_output.recipient == wallet_address:
                balance -= txin.parent_output.amount
        # Add all the money received by the address
        for txout in t.outputs:
            if txout.recipient == wallet_address:
                balance += txout.amount
    return balance


def verify_transaction(transaction):
    """
    Verify that the transaction is valid.
    We need to verify two things :
    - That all of the inputs of the transaction belong to the same wallet
    - That the transaction is signed by the owner of said wallet
    """
    tx_message = json.dumps(transaction.to_dict(include_signature=False))
    if isinstance(transaction, GenesisTransaction):
        # TODO: We should probably be more careful about validating genesis transactions
        return True

    # Verify input transactions
    for tx in transaction.inputs:
        if not verify_transaction(tx.transaction):
            logging.error("Invalid parent transaction")
            return False

    # Verify a single wallet owns all the inputs
    first_input_address = transaction.inputs[0].parent_output.recipient
    for txin in transaction.inputs[1:]:
        if txin.parent_output.recipient != first_input_address:
            logging.error(
                "Transaction inputs belong to multiple wallets (%s and %s)" %
                (txin.parent_output.recipient, first_input_address)
            )
            return False

    if not verify_signature(first_input_address, tx_message, transaction.signature):
        logging.error(
            "Invalid transaction signature, trying to spend someone else's money ?")
        return False

    # Call compute_fee here to trigger an assert if output sum is great than input sum. Without this,
    # a miner could put such an invalid transaction.
    compute_fee(transaction.inputs, transaction.outputs)

    return True


class Investment(Transaction):

    def __init__(self, sender_address, sender_private_key, recipient_address, value, url):
        self.url = url
        Transaction.__init__(self, sender_address, sender_private_key, recipient_address, value)

    def to_dict(self, include_signature=True):
        d = {
            "inputs": list(map(TransactionInput.to_dict, self.inputs)),
            "outputs": list(map(TransactionOutput.to_dict, self.outputs)),
            "fee": self.fee
        }

        if include_signature:
            d["signature"] = self.signature

        return d

    def to_dict(self):
        return OrderedDict({'sender_address': self.sender_address,
                            'recipient_address': self.recipient_address,
                            'value': self.value,
                            'url':self.url})
# class Transaction:

#     def __init__(self, sender_address, sender_private_key, recipient_address, value):
#         self.sender_address = sender_address
#         self.sender_private_key = sender_private_key
#         self.recipient_address = recipient_address
#         self.value = value

#     def __getattr__(self, attr):
#         return self.data[attr]

#     def to_dict(self):
#         return OrderedDict({'sender_address': self.sender_address,
#                             'recipient_address': self.recipient_address,
#                             'value': self.value})

#     def sign_transaction(self):
#         """
#         Sign transaction with private key
#         """
#         private_key = ECC.import_key(binascii.unhexlify(self.sender_private_key))
#         signer = DSS.new(private_key, 'fips-186-3')
#         h = SHA256.new(str(self.to_dict()).encode('utf8'))
#         return binascii.hexlify(signer.sign(h)).decode('ascii')