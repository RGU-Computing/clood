'use strict';

angular.module('cloodApp.global_config', [])
.config(['$stateProvider', function($stateProvider) {
  var globalConfigState = {
    name: 'global_config',
    url: '/global_config',
    templateUrl: 'global_config/global_config.html',
    controller: 'GlobalConfigCtrl'
  };
  
  $stateProvider.state(globalConfigState);
}])

.controller('GlobalConfigCtrl', ['$scope', 'ENV_CONST', '$log', function($scope, ENV_CONST, $log) {
  
  if (typeof ENV_CONST.base_api_url == 'undefined' || ENV_CONST.base_api_url == '') {
    $scope.pop("warn", null, "The root API to the serverless functions is not set. You can set this up in env.js");
  }

  // Updates the global config to reflect changes in clood service
  $scope.updateGlobalConfig = function() {
    $scope.createGlobalConfig(); // create config
    $scope.getGlobalConfig(); // get config
    location.reload();  // refresh page
  };
  
}]);
