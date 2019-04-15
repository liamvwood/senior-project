angular.module('BlockchainApp', [])

angular.module('BlockchainApp').controller('mainController', function ($http, $scope) {
    $scope.dump = document.querySelector('#dump')
    $scope.getChain = function () {
        console.log('debug')
        $http.get('/chain')
            .then(function (res) {
                dump.innerHTML = JSON.stringify(res);
            })
            .catch(function (err) {
                console.log(err);
            });
    }
    $scope.mine = function() {
        $http.get('/mine')
        .then(function (res) {
            dump.innerHTML = JSON.stringify(res);
        })
        .catch(function (err) {
            console.log(err);
        });
    }
    $scope.register = function() {
        let node = document.getElementById('node').value
        $http.post('/nodes/register', {'nodes':[node]})
        .then((res)=>{
            dump.innerHTML = JSON.stringify(res);
        })
    }
    $scope.resolve = function() {
        $http.get('/nodes/resolve')
        .then(function(res){
            dump.innerHTML = JSON.stringify(res);
        })
    }
    $scope.newTransaction = function() {
        let sender = document.getElementById('sender').value
        let recipient = document.getElementById('recipient').value
        let amount = document.getElementById('amount').value

        $http.post('/transactions/new', {'sender':sender, 'recipient': recipient, 'amount': amount})
        .then(function(res) {
            dump.innerHTML = JSON.stringify(res);
        })
    }
})