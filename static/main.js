angular.module('BlockchainApp', [])
    .config(['$interpolateProvider', function ($interpolateProvider) {
        $interpolateProvider.startSymbol('{[');
        $interpolateProvider.endSymbol(']}');
    }]);
angular.module('BlockchainApp').factory('blockchainFactory', function ($http) {

    var methods = {
        getChain: function () {
            return $http.get('/chain')
        },
        getNodes: function () {
            return $http.get('/nodes/get')
        },
        createWallet: function () {
            return $http.get('/wallet/new')
        },
        mine: function () {
            return $http.get('/mine')
        },
        registerNode: function (nodes) {
            return $http.post('/nodes/register', { 'nodes': [node] })
        },
        resolveNode: function () {
            return $http.get('/nodes/resolve')
        },
        createTransaction: function (sender, recipient, amount, private_key) {
            return $http.post('/generate/transaction', { 'sender_address': sender, 'sender_private_key': private_key, 'recipient_address': recipient, 'amount': amount })
        },
        submitTransaction: function (sender, recipient, amount, signature) {
            return $http.post('/transactions/new', { 'sender_address': sender, 'signature': signature, 'recipient_address': recipient, 'amount': amount })
        },
        createInvestment: function (sender, recipient, amount, private_key, url) {
            return $http.post('/generate/investment', { 'sender_address': sender, 'sender_private_key': private_key, 'recipient_address': recipient, 'amount': amount, 'url': url })
        },
        submitInvestment: function (sender, recipient, amount, signature, url) {
            return $http.post('/investments/new', { 'sender_address': sender, 'signature': signature, 'recipient_address': recipient, 'amount': amount, 'url': url })
        },
        getRedditJSON: function (url) {
            return $http.get(url)
        }
    }
    return methods;
})
function findWalletBalance(address, transactions) {
    var current_balance = 0
    for (let i = 0; i < transactions.length; i++) {
        if (transactions[i].recipient_address == address) {
            current_balance += transactions[i].value
        }
        if (transactions[i].sender_address == address) {
            current_balance -= transactions[i].value
        }
    }
    return current_balance
}

function myAlertTop() {
    $(".myAlert-top").show();
    setTimeout(function () {
        $(".myAlert-top").hide();
    }, 2000);
}
var isFirstUpsFound = false
function traverse(jsonObj) {
    if (jsonObj !== null && typeof jsonObj == "object") {
        Object.entries(jsonObj).forEach(([key, value]) => {
            // key is either an array index or object key
            if (key !== 'ups' && !isFirstUpsFound) {
                traverse(value);
            }
            else if (!isFirstUpsFound) {
                console.log(value)
                isFirstUpsFound = true
            }
        });
    }
    else {

    }
}

angular.module('BlockchainApp').controller('mainController', function (blockchainFactory, $http, $scope) {
    $scope.chain = []
    $scope.table_content = 'blockchain'
    blockchainFactory.getChain()
        .then(function (res) {
            $scope.chain = res.data['chain']
        })

    $scope.createWallet = function () {
        let private_key_text = document.getElementById('private_key')
        let public_key_text = document.getElementById('public_key')

        blockchainFactory.createWallet()
            .then(function (res) {
                private_key_text.value = res.data['private_key']
                public_key_text.value = res.data['public_key']
            })
    }
    $scope.mine = function () {
        blockchainFactory.mine()
            .then(function (res) {
            })
            .catch(function (err) {
                console.log(err);
            });
    }
    $scope.register = function () {
        let node = document.getElementById('node').value
        blockchainFactory.registerNode(node)
            .then((res) => {
            })
    }
    $scope.resolve = function () {
        blockchainFactory.resolveNode()
            .then(function (res) {
            })
    }
    $scope.createTransaction = function () {
        let sender = document.getElementById('sender_address').value
        let recipient = document.getElementById('recipient_address').value
        let private_key = document.getElementById('sender_private_key').value
        let amount = document.getElementById('amount').value

        let confirmation_sender = document.getElementById('confirmation_sender_address')
        let confirmation_recipient = document.getElementById('confirmation_recipient_address')
        let confirmation_amount = document.getElementById('confirmation_amount')
        let transaction_signature = document.getElementById('transaction_signature')


        blockchainFactory.createTransaction(sender, recipient, amount, private_key)
            .then(function (res) {
                signature = res.data['signature']
                transaction = res.data['transaction']
                confirmation_sender.value = transaction['sender_address']
                confirmation_recipient.value = transaction['recipient_address']
                confirmation_amount.value = transaction['value']
                transaction_signature.value = signature
            })
            .catch(function (err) {
                console.log(err)
            })
    }

    $scope.createInvestment = function () {
        let investment_sender = document.getElementById('investment_sender_address').value
        let investment_recipient = document.getElementById('investment_recipient_address').value
        let investment_private_key = document.getElementById('investment_sender_private_key').value
        let investment_amount = document.getElementById('investment_amount').value
        let investment_url = document.getElementById('investment_url').value

        let confirmation_investment_sender = document.getElementById('confirmation_investment_sender_address')
        let confirmation_investment_recipient = document.getElementById('confirmation_investment_recipient_address')
        let confirmation_investment_amount = document.getElementById('confirmation_investment_amount')
        let confirmation_investment_signature = document.getElementById('confirmation_investment_signature')
        let confirmation_url = document.getElementById('confirmation_investment_url')

        blockchainFactory.createInvestment(investment_sender, investment_recipient, investment_amount, investment_private_key, investment_url)
            .then(function (res) {
                signature = res.data['signature']
                transaction = res.data['transaction']
                confirmation_investment_sender.value = transaction['sender_address']
                confirmation_investment_recipient.value = transaction['recipient_address']
                confirmation_investment_amount.value = transaction['value']
                confirmation_url.value = transaction['url']
                confirmation_investment_signature.value = signature
            })
            .catch(function (err) {
                console.log(err)
            })
    }

    $scope.submitInvestment = function () {
        let sender = document.getElementById('confirmation_investment_sender_address').value
        let recipient = document.getElementById('confirmation_investment_recipient_address').value
        let amount = document.getElementById('confirmation_investment_amount').value
        let signature = document.getElementById('confirmation_investment_signature').value
        let url = document.getElementById('confirmation_investment_url').value
        blockchainFactory.submitInvestment(sender, recipient, amount, signature, url)
            .then(function (res) {
                if (res.status == 201) {
                    $('#investmentModal').modal('hide')
                    myAlertTop()
                }
            })
            .catch((err) => {
                console.log(err)
            })
    }

    $scope.submitTransaction = function () {
        let sender = document.getElementById('confirmation_sender_address').value
        let recipient = document.getElementById('confirmation_recipient_address').value
        let amount = document.getElementById('confirmation_amount').value
        let signature = document.getElementById('transaction_signature').value
        blockchainFactory.submitTransaction(sender, recipient, amount, signature)
            .then(function (res) {
                if (res.status == 201) {
                    $('#transactionModal').modal('hide')
                    myAlertTop()
                }
            })
            .catch((err) => {
                console.log(err)
            })
    }
    $scope.getNodes = function () {
        blockchainFactory.getNodes()
            .then(function (res) {
                var nodes = res.data['nodes']
                var node = "";
                for (i = 0; i < nodes.length; i++) {
                    //node = "<li>" + response['nodes'][i] + "</li>";
                    node = "<li> <a href=http://" + nodes[i] + ">" + nodes[i] + "</a></li>";
                    document.getElementById("list_nodes").innerHTML += node;
                };
            });
    }
    $scope.transactions = []
    blockchainFactory.getChain()
        .then(function (res) {
            $scope.chain = res.data['chain']
            var length = res.data['length']
            var transactions = []
            for (i = 1; i < length; i++) {
                for (j = 0; j < $scope.chain[i]["transactions"].length; j++) {
                    transactions.push($scope.chain[i]["transactions"][j]);
                }
            }
            $scope.all_transactions = transactions
        })
    $scope.investments = []

    $scope.changeTableView = function (selection) {
        var dropdownEl = document.getElementById('dropdown-text');
        if (selection == 'blockchain') {
            dropdownEl.innerHTML = 'Browser'
            blockchainFactory.getChain()
                .then(function (res) {
                    $scope.chain = res.data['chain']
                    $scope.table_content = 'blockchain'
                })
        }
        else if (selection == 'transactions') {
            dropdownEl.innerHTML = 'Transactions'
            blockchainFactory.getChain()
                .then(function (res) {
                    $scope.chain = res.data['chain']
                    var length = res.data['length']
                    var transactions = []
                    for (i = 1; i < length; i++) {
                        for (j = 0; j < $scope.chain[i]["transactions"].length; j++) {
                            if (!$scope.chain[i]["transactions"][j]['url']) {
                                transactions.push($scope.chain[i]["transactions"][j]);
                            }
                        }
                    }
                    $scope.transactions = transactions
                    $scope.table_content = 'transactions'
                })
        }
        else if (selection == 'investments') {
            dropdownEl.innerHTML = 'Investments'
            blockchainFactory.getChain()
                .then(function (res) {
                    $scope.chain = res.data['chain']
                    var length = res.data['length']
                    var investments = []
                    for (i = 1; i < length; i++) {
                        for (j = 0; j < $scope.chain[i]["transactions"].length; j++) {
                            if ($scope.chain[i]["transactions"][j]['url']) {
                                blockchainFactory.getRedditJSON(`${$scope.chain[i]["transactions"][j]['url']}/.json`)
                                    .then(function (res) {
                                        //that's all... no magic, no bloated framework
                                        traverse(res);
                                        isFirstUpsFound = false
                                    })
                                    .catch(function (err) {
                                        console.log(err)
                                    })
                                investments.push($scope.chain[i]["transactions"][j]);
                            }
                        }
                    }
                    $scope.investments = investments
                    $scope.table_content = 'investments'
                })
        }
    }

    $scope.formatDate = function (timestamp) {
        //format date 
        var options = { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" };
        var date = new Date(timestamp * 1000);
        return date.toLocaleTimeString("en-us", options);
    }

    $scope.toggleInvestmentCollapse = function () {
        if ($("#collapse1").attr("aria-expanded")) {
            $("#collapse1").collapse('hide')
        }
        $("#collapse2").collapse('toggle')
    }
    $scope.toggleTransactionCollapse = function () {
        if ($("#collapse2").attr("aria-expanded")) {
            $("#collapse2").collapse('hide')
        }
        $("#collapse1").collapse('toggle')
    }
    $scope.generateInvestment = function (investment_address) {
        let recipient = document.getElementById('recipient_address')
        recipient.value = investment_address
        if ($("#collapse2").attr("aria-expanded")) {
            $("#collapse2").collapse('hide')
        }
        $("#collapse1").collapse('show')
    }

    var wallet_balance = document.getElementById('wallet_balance')
    $('#input_wallet_balance').on('input', function (e) {
        var wallet_address = document.getElementById('input_wallet_balance').value
        wallet_balance.innerHTML = `${findWalletBalance(wallet_address, $scope.all_transactions)} RBC`
    });
})