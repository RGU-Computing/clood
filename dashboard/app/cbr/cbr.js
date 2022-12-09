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

.controller('CBRCtrl', ['$scope', '$http', '$state', 'ENV_CONST', '$uibModal', function($scope, $http, $state, ENV_CONST, $uibModal ) {
  $scope.datenow = new Date();  // current date for any date field selection
  $scope.menu.active = $scope.menu.items[2]; // ui active menu tag
  $scope.selected = {};
  $scope.requests = { current:  { data: [], topk: 5, globalSim: "Weighted Sum", explanation: true }, previous: [], response: null };

  // Retrieves all projects
  $scope.getAllProjects = function() {
    $http({method: 'GET', url: ENV_CONST.base_api_url + "/project", headers: {"Authorization":$scope.auth.token}}).then(function(res){
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
    // Check if the type is Array
    console.log("Current ", $scope.requests.current); // array attributes: name, value, weight, unknown, strategy (if unknown
    angular.forEach($scope.requests.current.data, function(value, key) {
      if (value.similarity == "Array" && value.value != "" && value.value != null) {
        value.value = value.value.split(",");
        if(value.type == "Integer") {
          value.value = value.value.map(function (el) { return parseInt(el); });
        } else if (value.type == "Float") {
          value.value = value.value.map(function (el) { return parseFloat(el); });
        }
      }
    });

    console.log("Current ", $scope.requests.current); // array attributes: name, value, weight, unknown, strategy (if unknown)
    $http.post(ENV_CONST.base_api_url + '/retrieve', $scope.requests.current, {headers:{"Authorization":$scope.auth.token}}).then(function(res) {
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

    // Convert csv input to array
    angular.forEach(newCase.project.attributes, function(value, key) {
      if (value.similarity == "Array") {
        newCase.data[value.name] = newCase.data[value.name].split(",");
        if (value.type == "Integer") {
          newCase.data[value.name] = newCase.data[value.name].map(function (el) { return parseInt(el); });
        } else if (value.type == "Float") {
          newCase.data[value.name] = newCase.data[value.name].map(function (el) { return parseFloat(el); });
        }
      console.log("newCase",newCase);
      }
    });

    $http.post(ENV_CONST.base_api_url + '/retain', newCase, {headers:{"Authorization":$scope.auth.token}}).then(function(res) {
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

  $scope.plotTest = function() {
    var attributes = [];
    var scores = [];

    $scope.requests.response.bestK.forEach(function(value, index) {
      var temp = [];
      var temp2 = [];
      value.match_explanation.forEach(function(value, index) {
        temp.push(value.similarity);
        temp2.push(value.field);
      });
      temp.push(value.score__);
      temp2.push("<b>Global Similarity</b>");
      scores.push(temp);
      attributes.push(temp2);
    });

    var traces = [];
    for (var i = 0; i < Math.min(scores.length,5); i++) {
      traces.push({
        x: attributes[i],
        y: scores[i],
        type: 'scatter',
        line: {shape: 'hvh'},
        name: "Case " + (i + 1)
      });
    }
    
    var data = traces;
    Plotly.newPlot('plotly-graph', data);
  };

  $scope.reuse = function() {
    $state.transitionTo('cbr.reuse');
  };

  $scope.graphData = function(entry) {
    var $ctrl = this;
    $ctrl.data = entry
    $ctrl.open = function (size) {
      var modalInstance = $uibModal.open({
        animation: true,
        backdrop: true,  // prevents closing modal by clicking outside it
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'cbr/views/modalviews/bargraph.html',
        controller: 'ModalGraphInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return $ctrl.data
          }
        }
      })
      modalInstance.result.then(function (res) {
        console.log("Graph modal closed");
      });
    };
    $ctrl.open('lg');
  };

  $scope.showCase = function(entry) {
    var $ctrl = this;
    $ctrl.data = entry
    $ctrl.open = function (size) {
      var modalInstance = $uibModal.open({
        animation: true,
        backdrop: true,  // prevents closing modal by clicking outside it
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'cbr/views/modalviews/caseView.html',
        controller: 'ModalCaseInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return $ctrl.data
          }
        }
      })
      modalInstance.result.then(function (res) {
        console.log("Case modal closed");
      });
    };
    $ctrl.open('lg');
  };


  // Start calls
  $scope.getAllProjects();
  $state.transitionTo('cbr.retrieve'); // REMOVE
}])
.controller('ModalGraphInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.data = angular.copy(data);
  console.log($scope.data);
  
  $scope.plotter = function(entry) {
    var attributes = [];
    var scores = [];


    entry.match_explanation.forEach(function(value, index) {
      scores.push(value.similarity);
      attributes.push(value.field);
    });
    //scores.push(entry.score__/scores.length);
    //attributes.push("Global Similarity");

    var trace = {
      x: attributes,
      y: scores,
      type: 'bar',
      //limit to 3 decimal places
      text: scores.map(function(value) {
        return value.toFixed(3);
      }),
      textposition: 'auto',
      marker: {
        color: 'rgb(91, 184, 83)',
        opacity: 0.7,
        line: {
          color: 'rgb(58, 128, 52)',
          width: 1.5
        }
      }
    };

    var layout = {
      title: 'Local Similarity Scores',
      autosize: true,
      width: 850,
      xaxis: {
        tickfont: {
          color: 'rgb(107, 107, 107)'
        },
        title: 'Attributes'
      },
      yaxis: {
        zeroline: true,
        gridwidth: 2,
        title: 'Similarity Scores'
      }
    };
    
    var data = [trace];
    Plotly.newPlot('bar-graph', data, layout);
  };
  
  $scope.save = function() {
    $uibModalInstance.close();
  };

  $scope.cancel = function() {
    $uibModalInstance.dismiss('cancel');
  };
}])
.controller('ModalCaseInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.data = angular.copy(data);
  console.log($scope.data);
  
  $scope.save = function() {
    $uibModalInstance.close();
  };

  $scope.cancel = function() {
    $uibModalInstance.dismiss('cancel');
  };
}]);
