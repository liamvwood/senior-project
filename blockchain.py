from collections import OrderedDict

import binascii

import Cryptodome
import Cryptodome.Random
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import ECC
from Cryptodome.Signature import DSS

import hashlib
import json
from time import time
from uuid import uuid4
import requests

from flask import Flask, jsonify, request, render_template
from urllib.parse import urlparse

from transaction import Transaction, TransactionInput, compute_balance
from block import Block, GenesisBlock
from wallet import Wallet


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.nodes = set()

        self.wallet = Wallet()

        # Store this nodes keys for "safe" keeping
        file_out = open("private.txt", "w")
        file_out.write(binascii.hexlify(
            self.wallet._private_key.export_key(format='DER')).decode('ascii'))

        file_out = open("receiver.txt", "w")
        file_out.write(binascii.hexlify(
            self.wallet._public_key.export_key(format='DER')).decode('ascii'))

        self.transactions = []

        # I haven't settled on a proof yet, looking into proof of stake
        self.new_block()

    def serialize_chain(self):
        serialized_chain = []
        for block in self.chain:
            serialized_chain.append(block.to_dict())

        return serialized_chain

    def register_node(self, address):
        # Adds a new node to the set of nodes
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        # Validate the node's blockchain list
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")

            # Check that the hash of each block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof is also correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        # Our consensus algorithm that updates to the longest chain in the network

        neighbours = self.nodes
        new_chain = None

        # We are looking for chains that are longer than ours
        max_length = len(self.chain)

        # Check all the chains in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check for a longer chain and check its validity
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, previous_block=None):
        # this method should create a new block and add it to the chain

        if not previous_block:
            block = GenesisBlock(self.wallet.address)
        else:
            block = Block(self.transactions, previous_block,
                          self.wallet.address)

        # block = {
        #     'index': len(self.chain) + 1,
        #     'timestamp': time(),
        #     'transactions': self.transactions,
        #     'proof': proof,
        #     'previous_hash': previous_hash or self.hash(self.chain[-1])
        # }

        # Clear transactions on creation of new block
        self.transactions = []

        # add new block to the chain
        self.chain.append(block)

        return block

    def verify_transaction_signature(self, sender_address, signature, transaction):
        """
        Check that the provided signature corresponds to transaction
        signed by the public key (sender_address)
        """
        pubkey = ECC.import_key(binascii.unhexlify(sender_address))
        verifier = DSS.new(pubkey, 'fips-186-3')
        h = SHA256.new(transaction.encode('utf8'))
        try:
            verifier.verify(h, binascii.unhexlify(signature))
            return True
        except ValueError:
            print('this signature is NOT authentic')
            return False

    def submit_transaction(self, sender_address, transaction, signature, url=None):
        """
        Add a transaction to transactions array if the signature verified
        """
        # if url == None:
        #     transaction = OrderedDict({'sender_address': sender_address,
        #                                'recipient_address': recipient_address,
        #                                'value': value
        #                                })
        # else:
        #     transaction = OrderedDict({'sender_address': sender_address,
        #                                'recipient_address': recipient_address,
        #                                'value': value,
        #                                'url': url
        #                                })
        # Manages transactions from wallet to another wallet
        transaction_verification = self.verify_transaction_signature(sender_address, signature, transaction)
        if transaction_verification:
            self.transactions.append(transaction)
            return len(self.chain) + 1
        else:
            return False

    def find_balance(self, address):
        balance = 0
        # parse the entire blockchain for transactions with address as recipient
        for block in self.chain:
            balance += compute_balance(address, block.get_transactions())

        # parse the current list of transactions
        balance += compute_balance(address, self.transactions)

        return balance

    @staticmethod
    def search_block_for_address(block, address):
        outputs = []
        for transaction in block.get_transactions():
            for i in range(len(transaction.outputs)):
                if transaction.outputs[i].recipient == address:
                    outputs.append((transaction, i))

        return outputs

    def get_transaction_inputs(self, address, amount):
        chosen_inputs = []
        potential_inputs = []

        for block in self.chain:
            potential_inputs = self.search_block_for_address(block, address)

        if len(potential_inputs) == 0:
            return None

        sum_chosen_inputs = 0

        while (sum_chosen_inputs < amount and len(potential_inputs) > 0):
            max_value = potential_inputs[0][0].outputs[potential_inputs[0][1]].amount
            max_pos = 0

            for i in range(1, len(potential_inputs)):
                if max_value < potential_inputs[i][0].outputs[potential_inputs[i][1]].amount:
                    max_value = potential_inputs[i][0].outputs[potential_inputs[i][1]].amount
                    max_pos = 0

            chosen_inputs.append(potential_inputs[max_pos])
            sum_chosen_inputs += max_value
            potential_inputs.pop(max_pos)

        input_transactions = []

        for _input in chosen_inputs:
            input_transactions.append(TransactionInput(_input[0], _input[1]))

        return input_transactions

    @staticmethod
    def hash(block):
        # hashes a passed in block using SHA-256

        # Asserts that the block object is ordered
        block_string = json.dumps(block, sort_keys=True).encode()

        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # gets the last block in the chain
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Proof of Work Algorithm:
        - Find a number p' such that hash(p*p') contains leading 4 zeroes,
        and where p is the previous proof nad p' is the new proof
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        # validates the proof, returns <bool>

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
