'use strict';

// Declare app level module which depends on views, and core components
angular.module('cloodApp', [
  'cloodApp.env',
  'ui.router',
  'ngResource',
  'ngAnimate',
  'toaster',
  'cloodApp.projects',
  'cloodApp.config',
  'cloodApp.cbr',
  'cloodApp.version'
]).
config(['$locationProvider', '$urlRouterProvider', '$stateProvider', function($locationProvider, $urlRouterProvider, $stateProvider) {
  $locationProvider.hashPrefix('');
  $urlRouterProvider.otherwise('/projects');
}]).
// inject $state into all views
run(['$rootScope', '$state', '$stateParams', function($rootScope, $state, $stateParams){
  $rootScope.$state = $state;
  $rootScope.$stateParams = $stateParams;
}]).
// UI notifications in view
run(['$rootScope', 'toaster', function($rootScope, toaster){
  $rootScope.pop = function(type, title, msg) {
    toaster.pop(type, title, msg);
  };
}]).
// Global variables?
run(['$rootScope', function($rootScope){
  var menu = {};
  menu.items = ['Projects', 'Configuration', 'CBR Tasks'];
  menu.active = menu.items[0];
  $rootScope.menu = menu;
}]).
// App-wide functions
run(['$rootScope', '$http', 'ENV_CONST', function($rootScope, $http, ENV_CONST){ // global functions
  $rootScope.getGlobalConfig = function() {
    $http.get(ENV_CONST.base_api_url + "/config").then(function(res) {
      if (typeof res.data.attributeOptions != 'undefined'){
        $rootScope.globalConfig = res.data; // should allow update in settings
      }
    });
  };
  $rootScope.getDataType = function(data) { // number, string, boolean, object, undefined
    return typeof data;
  };
  $rootScope.objOrArrayHasContent = function(data) {
    if ((typeof data[0] != 'undefined') || (typeof Object.keys(data)[0] != 'undefined')) {
      return true;
    } else {
      return false;
    }
  };
  $rootScope.getGlobalConfig();
}]).

directive('disallowSpaces', [function(){
  return {
    restrict: 'A',
    link: function($scope, $element) {
      $element.bind('input', function(){
        $(this).val($(this).val().replace(/ /g, ''));
      });
    }
  }
}]);
