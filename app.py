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
from flask_socketio import SocketIO
from urllib.parse import urlparse


from blockchain import Blockchain
from transaction import Investment, Transaction, TransactionOutput
from wallet import Wallet

import binascii
import Cryptodome
from Cryptodome.PublicKey import ECC
from flask_cors import CORS

MINING_SENDER = 0


### Setting up our Blockchain as an API with Flask ###

# Instantiate our Flask Node
app = Flask(__name__)

# Instantiate our blockchain
blockchain = Blockchain()

print(blockchain.wallet.address)

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/configure', methods=['GET', 'POST'])
def configure():
    return render_template('configure.html')

@app.route('/make/transaction')
def make_transaction():
    return render_template('./make_transaction.html')

@app.route('/view/transactions')
def view_transaction():
    return render_template('./view_transactions.html')

@app.route('/wallet/new', methods=['GET'])
def new_wallet():
    wallet = blockchain.wallet
    private_key = wallet._private_key

    response = {
        'private_key': binascii.hexlify(private_key.export_key(format='DER')).decode('ascii'),
        'public_address': wallet.address,
        'public_key': wallet.public_key()
    }

    return jsonify(response), 200


@app.route('/mine', methods=['GET'])
def mine():
    # run the proof of work to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We doll out the reward for mining the block here
    # And we represent the sender as "0" which refers to the current node as the miner
    blockchain.submit_transaction(sender_address=MINING_SENDER, recipient_address=blockchain.wallet.address, value=1, signature="")

    # Now create the new block on the blockchain
    block = blockchain.new_block(previous_block=last_block)
    # previous_hash= blockchain.hash(last_block)
    # block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Added",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200

@app.route('/generate/investment', methods=['POST'])
def generate_investment():
    values = request.get_json()

    sender_address = values['sender_address']
    sender_private_key = values['sender_private_key']
    recipient_address = values['recipient_address']
    value = values['amount']
    url = values['url']

    investment = Investment(sender_address, sender_private_key, recipient_address, value, url)

    response = {'transaction': investment.to_dict(), 'signature': investment.sign_transaction()}

    return jsonify(response), 200

@app.route('/investments/new', methods=['POST'])
def new_investment():
    values = request.get_json()
    # Check that the required fields are in the POST'ed data
    required = ['sender_address', 'recipient_address', 'amount', 'signature', 'url']
    if not all(k in values for k in required):
        return 'Missing values', 400
    # Create a new Transaction
    transaction_result = blockchain.submit_transaction(values['sender_address'], values['recipient_address'], values['amount'], values['signature'], url=values['url'])

    if transaction_result == False:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406
    else:
        response = {'message': 'Investment will be added to Block '+ str(transaction_result)}
        return jsonify(response), 201

@app.route('/generate/transaction', methods=['POST'])
def generate_transaction():
    values = request.get_json()

    sender_address = values['sender_address']
    sender_private_key = values['sender_private_key']
    recipient_address = values['recipient_address']
    amount = int(values['amount'])

    wallet = Wallet(private_key=sender_private_key)

    inputs = blockchain.get_transaction_inputs(wallet.address, amount)

    if not inputs:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406

    outputs = [TransactionOutput(recipient_address,amount)]

    transaction = Transaction(wallet, inputs, outputs)
    
    response = {'sender_address':sender_address, 'recipient_address': recipient_address, 'amount': amount, 'transaction': transaction.to_dict(), 'signature': transaction.signature}

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    # Check that the required fields are in the POST'ed data
    required = ['transaction', 'sender_address', 'signature']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    transaction_result = blockchain.submit_transaction(values['sender_address'], values['transaction'], values['signature'])

    if transaction_result == False:
        response = {'message': 'Invalid Transaction!'}
        return jsonify(response), 406
    else:
        response = {'message': 'Transaction will be added to Block '+ str(transaction_result)}
        return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.serialize_chain(),
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/get', methods=['GET'])
def get_nodes():
    nodes = list(blockchain.nodes)
    response = {
        'nodes': nodes
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

@app.route('/balance', methods=['POST'])
def compute_balance():
    values = request.get_json()

    address = values.get('address')
    if address is None:
        return "Error: Please supply a valid address", 400

    balance = blockchain.find_balance(address)

    response = {
        'message': 'Computed balance',
        'balance': balance
    }

    return jsonify(response), 201

if __name__ == '__main__':
    socketio = SocketIO(app)
    socketio.run(app)