'use strict';

angular.module('cloodApp.config', [])
.config(['$stateProvider', function($stateProvider) {
  var configState = {
    name: 'config',
    url: '/config',
    templateUrl: 'config/config.html',
    controller: 'ProjectConfigCtrl'
  };
  var configAttributesState = {
    name: 'config.attributes',
    templateUrl: 'config/views/attributes.html'
  };
  var configAddDataState = {
    name: 'config.add_data',
    templateUrl: 'config/views/add_data.html'
  };
  $stateProvider.state(configState);
  $stateProvider.state(configAttributesState);
  $stateProvider.state(configAddDataState);
}])
.directive('customOnChange', [function() {
  return {
    restrict: 'A',
    link: function (scope, element, attrs) {
      var onChangeHandler = scope.$eval(attrs.customOnChange);
      element.on('change', onChangeHandler);
      element.on('$destroy', function() {
        element.off();
      });

    }
  };
}])
.factory('Project', ['$resource', 'ENV_CONST', function($resource, ENV_CONST) {
  return $resource(ENV_CONST.base_api_url + "/project" + '/:id', null, {
    'update': { method: 'PUT'}
  });
}])
.controller('ProjectConfigCtrl', ['$scope', '$http', '$state', 'Project', 'ENV_CONST', function($scope, $http, $state, Project, ENV_CONST) {
  $scope.menu.active = $scope.menu.items[1]; // ui active menu tag
  $scope.selected = {};
  $scope.newAttrib = {};
  $scope.newCasebase = {'data':[], 'columnHeads':[], 'preview':false};

  // Get all projects
  $scope.getAllProjects = function() {
    $http.get(ENV_CONST.base_api_url + "/project").then(function(res){
      $scope.projects = res.data; // array of projects
      if ($scope.projects.length > 0) {
        $scope.selectProject($scope.projects[0]); // select first
      }
    });
  };

  $scope.selectProject = function(item) {
    console.log(item);
    $scope.selected = item;
  };

  $scope.addAttribute = function(item) {
    console.log(item);
    console.log($scope.selected);
    if (!containsObject(item, $scope.selected.attributes)) {
      $scope.selected.attributes.push(angular.copy(item)); // add to the selected project's attributes
    } else {
      console.log('Cannot have duplicate attribute names');
    }
    // update projects
    $scope.newAttrib.name = ""; // rest
  };

 // Removes attribute from project attributes list if it exists
  $scope.removeAttribute = function(item) {
    for (var i = 0; i < $scope.selected.attributes.length; i++) {
      if ($scope.selected.attributes[i].name === item.name) {
        $scope.selected.attributes.splice(i,1);
        break;
      }
    }
  };

  // UPDATE should create or update index depending on whether a casebase exists for the project
  $scope.updateProject = function() {
    var projId = $scope.selected.id__;
    var proj = angular.copy($scope.selected);
    console.log(proj);
    Project.update({ id: projId }, $scope.selected).$promise.then(
      function(suc) {
        console.log('Updated casebase attributes');
        $scope.pop("success", null, "Project updated.");
      }, function (err) {
        console.log(err);
        console.log('Error adding new attributes');
      });
  };

  // Create index mapping for a project. Index mapping specifies the case structure and is a required step before adding cases
  $scope.createIndexMapping = function() {
    $http.get(ENV_CONST.base_api_url + "/project" + "/mapping/" + $scope.selected.id__).then(function(res) {
      $scope.pop("success", null, "Project case-base has been set up.");
      $scope.selected.hasCasebase = true;
      console.log(res.data);
    }, function (err) {
      console.log(err);
      console.log("Error setting up the project's case-base");
    });
  };

  // Get allowed similarity metric for a data type
  $scope.getSimilarityTypes = function(type) {
    if (typeof type != 'undefined' && type != null) {
      var res = $scope.globalConfig.attributeOptions.find(obj => {
        return obj.type === type
      });
      return res.similarityTypes;
    }
  };

  // Checks if an object is in a list of objects using 'name' attribute
  function containsObject(obj, list) {
    var i;
    for (i = 0; i < list.length; i++) {
      if (list[i].name === obj.name) {
        return true;
      }
    }
    return false;
  }

  $scope.parseFile = function(file) {
    $scope.newCasebase = {'data':[], 'columnHeads':[], 'preview':false}; // reset
    $scope.displayWarning = "";
    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
    	complete: function(results) {
    		console.log(results); // results.data is the json object
        console.log(results.errors.length + " error(s) while parsing file.");
        if ("," === results.meta.delimiter.trim() || "\t" === results.meta.delimiter.trim()) { // we only accept commas and tabs as delimiters of valid csv
          $scope.newCasebase.columnHeads = results.meta.fields; // array of column headers
          $scope.newCasebase.data = results.data;
          // Attempt fix for error where last lines are empty (type: "FieldMismatch" code: "TooFewFields")
          var i;
          for (i = results.errors.length-1; i >= 0; i--) { // reverse so that subsequent rows and data indices match after any deletions
            if (results.errors[i].type === "FieldMismatch" && results.errors[i].code === "TooFewFields") {
              var numOfFields = Object.keys($scope.newCasebase.data[results.errors[i].row]).length;
              var valOfFirstField = $scope.newCasebase.data[results.errors[i].row][Object.keys($scope.newCasebase.data[results.errors[i].row])[0]];
              if (numOfFields === 1 && (valOfFirstField === null || "" === valOfFirstField.trim())) {
                $scope.newCasebase.data.splice(results.errors[i].row, 1);
              }
            }
          }
          // Check if supplied column heads match the expected fields
          var attribNameArray = $scope.selected.attributes.map(function (el) { return el.name; });
          if (!(attribNameArray.length === $scope.newCasebase.columnHeads.length && attribNameArray.sort().every(function(value, index) { return value === $scope.newCasebase.columnHeads.sort()[index]}))) {
            $scope.displayWarning = "Warning: One or more field names in CSV file are different from defined attributes. Names are case-sensitive. \n";
            $scope.displayWarning += "Attribute names: " + attribNameArray.toString() + ". \n";
            $scope.displayWarning += "CSV column names: " + $scope.newCasebase.columnHeads.toString() + ".";
          }
          console.log($scope.newCasebase);
        } else {
          alert('Could not parse file as file may not be CSV. No valid delimiter found.');
        }
    	}
    });
  };

  // jQuery!
  // $("#customFile").change(function() {
  //   console.log('Here');
  //   $scope.$apply(parseFile(this));
  // });

  $scope.readFile = function(event) {
    var files = event.target.files;
    console.log(files);
    // $scope.$apply(parseFile(files));
    $scope.parseFile(files[0]);
  };

  // Save casebase
  $scope.saveCasebase = function() {
    console.log($scope.newCasebase);
    $http.post(ENV_CONST.base_api_url + "/case/" + $scope.selected.id__ + "/list", $scope.newCasebase.data)
        .then(function(res) {
          console.log(res);
          $scope.newCasebase = {'data':[], 'columnHeads':[], 'preview':false}; // reset
          $scope.selected.hasCasebase = true;
          $scope.pop("success", null, "Data added.");
        })
        .catch(function(err) {
          console.log(err);
          $scope.pop("error", null, "An error occurred while trying to save data.");
        });
  };

  $scope.getAllProjects();
  // $scope.getGlobalConfig();
  $state.transitionTo('config.attributes');
}]);
