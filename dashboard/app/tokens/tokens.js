'use strict';

angular.module('cloodApp.tokens', [])
.config(['$stateProvider', function($stateProvider) {
  var tokensState = {
    name: 'tokens',
    url: '/tokens',
    templateUrl: 'tokens/tokens.html',
    controller: 'TokenCtrl'
  };
  $stateProvider.state(tokensState);
}])
.controller('TokenCtrl', ['$scope', '$http', 'Project', 'ENV_CONST', function($scope, $http, Token, ENV_CONST) {
    $scope.menu.active = $scope.menu.items[3]; // ui active menu tag
    $scope.projects = [];
    $scope.tokens = [];
    $scope.newToken = null; // new token to be saved
    
    if (typeof ENV_CONST.base_api_url == 'undefined' || ENV_CONST.base_api_url == '') {
        $scope.pop("warn", null, "The root API to the serverless functions is not set. You can set this up in env.js");
    }
    
    $scope.getAllProjects = function() {
        $http({method: 'GET', url: ENV_CONST.base_api_url + "/project", headers: {"Authorization":$scope.auth.token}}).then(function(res) {
            $scope.projects = res.data;
            console.log(res.data);
        });
    };

    $scope.getAllTokens = function() {
        $http({method: 'GET', url: ENV_CONST.base_api_url + "/token", headers: {"Authorization":$scope.auth.token}}).then(function(res) {
            $scope.tokens = res.data;
            //Iterate through tokens and add expiry date
            for (var i = 0; i < $scope.tokens.length; i++) {
                var date = new Date($scope.tokens[i].expiry);
                $scope.tokens[i].expiryDate = date.getHours() + ":" + ('0'+date.getMinutes()).slice(-2) + ":00 " + date.getDate() + "/" + (date.getMonth() + 1) + "/" + date.getFullYear();
            }
            console.log(res.data);
        });
    };

    $scope.getDate = function(value) {
        console.log("test", value);
        var date;
        switch(value) {
            case 0:
                date = new Date(Date.now()+(90*60*1000));
                break;
            case 1:
                date = new Date(Date.now()+(24*60*60*1000));
                break;
            case 2:
                date = new Date(Date.now()+(7*24*60*60*1000));
                break;
            case 3:
                date = new Date(Date.now()+(30*24*60*60*1000));
                break;
        }
        console.log("test2", value);
        $scope.newToken.expiryDate = date.getHours() + ":" + ('0'+date.getMinutes()).slice(-2) + ":00 " + date.getDate() + "/" + (date.getMonth() + 1) + "/" + date.getFullYear();
    };

    $scope.createToken = function() {
        console.log("token: " + $scope.newToken.name);
        switch($scope.newToken.value) {
            case '0':
                $scope.newToken.expiry = Date.now()+(90*60*1000);
                break;
            case '1':
                $scope.newToken.expiry = Date.now()+(24*60*60*1000);
                break;
            case '2':
                $scope.newToken.expiry = Date.now()+(7*24*60*60*1000);
                break;
            case '3':
                $scope.newToken.expiry = Date.now()+(30*24*60*60*1000);
                break;
        }
        var item = angular.copy($scope.newToken);
        var token = new Token($scope.newToken);
        console.log("new token: ", token);
        $http.post(ENV_CONST.base_api_url + "/token", token, {headers:{"Authorization":$scope.auth.token}}).then(function(res){
            console.log("res",res);
            item.id__ = res.data.token.id__;
            item.expiryDate = $scope.formatDate(item.expiry);
            item.token = res.data.token.token;
            $scope.tokens.push(item); // refresh list
            $scope.pop("success", null, "New token save.");
            $scope.newToken = null; // reset form fields
            //$scope.getAllTokens();
        }, function(err){
            console.log(err);
            $scope.pop("error", null, "Error saving new token.");
        });
    };

  // Deletes a token
  $scope.deleteToken = function(item) {
    $http({method: 'DELETE', url: ENV_CONST.base_api_url + "/token/" + item.id__, headers: {"Authorization":$scope.auth.token}}).then(function(){
      $scope.tokens = $scope.tokens.filter(function(el) { return el.id__ != item.id__; });
      $scope.pop("success", null, "Token deleted!");
      $scope.newToken = null; // cancel any selection on ui
    }, function(err){
      console.log(err);
      $scope.pop("error", null, "Item was not deleted as something went wrong.")
    })
  };

  // Copy token to clipboard
    $scope.copyToken = function(item) {
        navigator.clipboard.writeText(item);
        $scope.pop("success", null, "Token copied to clipboard!");
    };

  // Return a formatted date
    $scope.formatDate = function(date) {
        var d = new Date(date);
        return d.getHours() + ":" + ('0'+d.getMinutes()).slice(-2) + ":00 " + d.getDate() + "/" + (d.getMonth() + 1) + "/" + d.getFullYear();
    };

    $scope.getAllProjects();
    $scope.getAllTokens();
}]);