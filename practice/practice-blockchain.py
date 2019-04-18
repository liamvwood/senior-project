# Created using the guide at https://hackernoon.com/learn-blockchains-by-building-one-117428612f46
import hashlib
import json
from time import time
from uuid import uuid4
import requests

from flask import Flask, jsonify, request, render_template
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.nodes = set()

        # current origin node for getting onto the network
        self.nodes.add("192.168.0.156:5000")
        self.current_transactions = []

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
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # Clear transactions on creation of new block
        self.current_transactions = []

        # add new block to the chain
        self.chain.append(block)

        return block
    
    def new_transaction(self, sender, recipient, amount):
        # this method should create a new transacation and add it to the current_transactions

        # need to add a way to verify transactions

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['index'] + 1

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

### Setting up our Blockchain as an API with Flask ###

# Instantiate our Flask Node
app = Flask(__name__)

# Create a unique global address
node_indentifier = str(uuid4()).replace('-','')

# Instantiate our blockchain
blockchain = Blockchain()

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/mine', methods=['GET'])
def mine():
    # run the proof of work to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We doll out the reward for mining the block here
    # And we represent the sender as "0" which refers to the current node as the miner
    blockchain.new_transaction(
        sender="0",
        recipient=node_indentifier,
        amount=1
    )

    # Now create the new block on the blockchain
    previous_hash= blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Added",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # validate the request
    required_fields = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required_fields):
        return 'Missing values', 400
    
    # Otherwise, create the new transaction here
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {
        'message': f'Transaction is being added to Block {index}'
        }
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was updated!',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)