'use strict';

angular.module('cloodApp.cbr', [])

.config(['$stateProvider', function($stateProvider) {
  var cbrState = {
    name: 'cbr',
    url: '/cbr',
    templateUrl: 'cbr/cbr.html',
    controller: 'CBRCtrl'
  };
  var cbrRetrieveState = {
    name: 'cbr.retrieve',
    templateUrl: 'cbr/views/retrieve.html'
  };
  var cbrReuseState = {
    name: 'cbr.reuse',
    templateUrl: 'cbr/views/reuse.html'
  };
  var cbrReviseState = {
    name: 'cbr.revise',
    templateUrl: 'cbr/views/revise.html'
  };
  var cbrRetainState = {
    name: 'cbr.retain',
    templateUrl: 'cbr/views/retain.html'
  };

  $stateProvider.state(cbrState);
  $stateProvider.state(cbrRetrieveState);
  $stateProvider.state(cbrReuseState);
  $stateProvider.state(cbrReviseState);
  $stateProvider.state(cbrRetainState);
}])

.controller('CBRCtrl', ['$scope', '$http', '$state', 'ENV_CONST', function($scope, $http, $state, ENV_CONST) {
  $scope.datenow = new Date();  // current date for any date field selection
  $scope.menu.active = $scope.menu.items[2]; // ui active menu tag
  $scope.selected = {};
  $scope.requests = { current:  { data: [], topk: 5, globalSim: "Weighted Sum", explanation: false }, previous: [], response: null };

  // Retrieves all projects
  $scope.getAllProjects = function() {
    $http.get(ENV_CONST.base_api_url + "/project").then(function(res){
      $scope.projects = res.data; // array of projects
      if ($scope.projects.length > 0) {
        $scope.selected = $scope.projects[0]; // select first
        $scope.selectProject();
      }
    });
  };

  // selects a project
  $scope.selectProject = function() {
    console.log($scope.selected);
    if ($scope.selected.hasCasebase) {
      console.log("Project has a casebase");
      $state.transitionTo('cbr.retrieve');
    }
    // reset any previous selections
    $scope.editing = false;
    $scope.requests = { current:  { data: [], topk: 5, globalSim: "Weighted Sum", explanation: false }, previous: [], response: null };
  };

  // retrieves cases from the casebase using specified request features
  $scope.retrieveCases = function() {
    $scope.requests.current.project = angular.copy($scope.selected);
    console.log($scope.requests.current); // array attributes: name, value, weight, unknown, strategy (if unknown)
    $http.post(ENV_CONST.base_api_url + '/retrieve', $scope.requests.current).then(function(res) {
      $scope.requests.response = res.data;
      console.log($scope.requests.response)
      $state.transitionTo('cbr.reuse');
      $scope.pop("success", null, "Cases retrieved.");
    }).catch(function(err) {
      console.log(err);
      $scope.pop("error", null, "An error occurred while trying to retrieve cases.");
    });
  };

  // copies a retrieved case into the recommended case
  $scope.reuseCase = function(item) {
    var newCopy = {};
    angular.forEach($scope.requests.response.recommended, function(value, key) { // loop and use property indices to only copy casebase attributes
      newCopy[key] = angular.copy(item[key]);
    });
    $scope.requests.response.recommended = newCopy;
  };

  // Navigates to Revise page and reveal input fields for case editing
  $scope.reviseCase = function() {
    $scope.editing = true; // turn ui case editing on
    $scope.caseCopy = angular.copy($scope.requests.response.recommended); // keep copy of the case
    $state.transitionTo('cbr.revise');
  };

  $scope.retainCase = function() {
    $state.transitionTo('cbr.retain');
  };

  // saves a new case to the casebase
  $scope.saveCase = function() {
    var newCase = {};
    newCase.data = $scope.requests.response.recommended;
    newCase.project = $scope.selected;
    $http.post(ENV_CONST.base_api_url + '/retain', newCase).then(function(res) {
      console.log(res.data);
      $scope.pop("success", null, "New case added.");
      $state.transitionTo('cbr.retrieve');
    }).catch(function(err) {
      console.log(err);
      $scope.pop("error", null, "Case added was not added. Duplicate cases are rejected when not allowing duplicates.");
    });
  };

  // Get allowed reuse strategies for a data type
  $scope.getReuseStrategies = function(type) {
    if (typeof type != 'undefined' && type != null) {
      var res = $scope.globalConfig.attributeOptions.find(obj => {
        return obj.type === type
      });
      return res.reuseStrategy;
    }
  };

  // Hides case editing fields are restores case values to earlier state
  $scope.cancelReviseCase = function() {
    // $scope.editing = false; // turn ui case editing on
    $scope.requests.response.recommended = $scope.caseCopy; // keep copy of the case
    $state.transitionTo('cbr.reuse');
  };

  //Export query results to csv file
  $scope.exportResults = function(){
    let itemJSON = ""
    $scope.selected.attributes.forEach(function(value,index){
      index == 0 ? itemJSON += value.name : itemJSON += ","+value.name
    });
    $scope.requests.response.bestK.forEach(function(item,index){
      itemJSON += "\n"
      let caseValue;
      $scope.selected.attributes.forEach(function(key,index){
        item[key.name] == null ? caseValue = "" : caseValue = item[key.name]
        caseValue = caseValue.toString().replace(/[,\n]/gm, ' ');
        index == 0 ? itemJSON += caseValue : itemJSON += ","+caseValue
      });
    });

    let dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(itemJSON);
    let fileName = "clood-"+$scope.selected.id__+'-query.csv';

    let downloadLink = document.createElement('a');
    downloadLink.setAttribute('href', dataUri);
    downloadLink.setAttribute('download', fileName);
    downloadLink.click();

    $scope.pop("success", null, "Downloading cases as CSV");
  };


  // Start calls
  $scope.getAllProjects();
  $state.transitionTo('cbr.retrieve'); // REMOVE
}]);
