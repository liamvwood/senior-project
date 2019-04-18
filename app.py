'''
My blockchain implementation based off of [1], with additions from [2] and my own use case
References:
[1] https://github.com/dvf/blockchain/blob/master/blockchain.py
[2] https://github.com/adilmoujahid/blockchain-python-tutorial/blob/master/blockchain/blockchain.py
'''
import hashlib
import json
from time import time
from uuid import uuid4
import requests

from flask import Flask, jsonify, request, render_template
from urllib.parse import urlparse


from blockchain import Blockchain
from transaction import Transaction

import binascii
import Cryptodome
from Cryptodome.PublicKey import RSA

### Setting up our Blockchain as an API with Flask ###

# Instantiate our Flask Node
app = Flask(__name__)

# Create a unique global address
node_indentifier = str(uuid4()).replace('-','')

# Instantiate our blockchain
blockchain = Blockchain()

@app.route('/make/transaction')
def make_transaction():
    return render_template('./make_transaction.html')

@app.route('/view/transactions')
def view_transaction():
    return render_template('./view_transactions.html')

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
	random_gen = Cryptodome.Random.new().read
	private_key = RSA.generate(1024, random_gen)
	public_key = private_key.publickey()
	response = {
		'private_key': binascii.hexlify(private_key.exportKey(format='DER')).decode('ascii'),
		'public_key': binascii.hexlify(public_key.exportKey(format='DER')).decode('ascii')
	}

	return jsonify(response), 200

@app.route('/generate/transaction', methods=['POST'])
def generate_transaction():
	
	sender_address = request.form['sender_address']
	sender_private_key = request.form['sender_private_key']
	recipient_address = request.form['recipient_address']
	value = request.form['amount']

	transaction = Transaction(sender_address, sender_private_key, recipient_address, value)

	response = {'transaction': transaction.to_dict(), 'signature': transaction.sign_transaction()}

	return jsonify(response), 200


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