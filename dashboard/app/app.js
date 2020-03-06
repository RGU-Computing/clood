'use strict';

const base_api_url = "https://gmf6n4v3pb.execute-api.eu-west-2.amazonaws.com/dev";
const project_url = base_api_url + "/project";
const config_url = base_api_url + "/config";
// Declare app level module which depends on views, and core components
angular.module('myApp', [
  'ui.router',
  'ngResource',
  'ngAnimate',
  'toaster',
  'myApp.projects',
  'myApp.config',
  'myApp.cbr',
  'myApp.version'
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
run(['$rootScope', '$http', function($rootScope, $http){ // global functions
  $rootScope.getGlobalConfig = function() {
    $http.get(config_url).then(function(res) {
      if (typeof res.data.attributeOptions != 'undefined'){
        $rootScope.globalConfig = res.data; // should allow update in settings
      }
    });
  };
  $rootScope.getDataType = function(data) { // number, string, boolean, object, undefined
    return typeof data;
  };
  $rootScope.objOrArrayHasContent = function(data) {
    console.log(typeof data[0]);
    console.log(typeof Object.keys(data)[0]);

    if ((typeof data[0] != 'undefined') || (typeof Object.keys(data)[0] != 'undefined')) {
      console.log('Here');
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

// .directive('a', [function() {
//   return {
//     restrict: 'E',
//     link: function(scope, elem, attrs) {
//       elem.on('click', function(e) {
//         if (attrs.disabled) {
//           e.preventDefault(); // prevent link click
//         }
//       });
//     }
//   };
// }]);
