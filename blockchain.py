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

from transaction import Transaction

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.nodes = set()
        # Create a unique global address
        private_key = ECC.generate(curve='P-256')
        public_key = private_key.public_key()
        file_out = open("private.txt", "w")
        file_out.write(binascii.hexlify(private_key.export_key(format='DER')).decode('ascii'))

        file_out = open("receiver.txt", "w")
        file_out.write(binascii.hexlify(public_key.export_key(format='DER')).decode('ascii'))

        self.node_id = binascii.hexlify(public_key.export_key(format='DER')).decode('ascii')

        self.transactions = []

        # I haven't settled on a proof yet, looking into proof of stake
        self.new_block(previous_hash=1, proof=100)

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

    def new_block(self, proof, previous_hash=None):
        # this method should create a new block and add it to the chain
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

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
        public_key = ECC.import_key(binascii.unhexlify(sender_address))
        verifier = DSS.new(public_key, 'fips-186-3')
        h = SHA256.new(str(transaction).encode('utf8'))
        try:
            verifier.verify(h, binascii.unhexlify(signature))
            return True
        except ValueError:
            print('this signature is NOT authentic')
            return False
        # return verifier.verify(h, binascii.unhexlify(signature))


    def submit_transaction(self, sender_address, recipient_address, value, signature, url=None):
        """
        Add a transaction to transactions array if the signature verified
        """
        if url == None:
            transaction = OrderedDict({'sender_address': sender_address,
                                    'recipient_address': recipient_address,
                                    'value': value
                                    })
        else:
            transaction = OrderedDict({'sender_address': sender_address,
                                    'recipient_address': recipient_address,
                                    'value': value,
                                    'url': url
                                    })
        #Reward for mining a block
        if sender_address == 0:
            self.transactions.append(transaction)
            return len(self.chain) + 1
        #Manages transactions from wallet to another wallet
        else:
            transaction_verification = self.verify_transaction_signature(
                sender_address, signature, transaction)
            if transaction_verification:
                self.transactions.append(transaction)
                return len(self.chain) + 1
            else:
                return False


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