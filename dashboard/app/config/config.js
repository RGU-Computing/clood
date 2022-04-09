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
//.controller('TableModalController', ['$scope', 'close', function($scope, close) {
//
// $scope.dismissModal = function(result) {
//    console.log('in modal controller');
// 	close(result, 200); // close, but give 200ms for bootstrap to animate
// };
//
//}])
.controller('ProjectConfigCtrl', ['$scope', '$http', '$state', 'Project', 'ENV_CONST', '$uibModal', '$log', function($scope, $http, $state, Project, ENV_CONST, $uibModal, $log) {
  $scope.menu.active = $scope.menu.items[1]; // ui active menu tag
  $scope.selected = {};
  $scope.newAttrib = {};
  $scope.newCasebase = {'data':[], 'columnHeads':[], 'preview':false};
  $scope.editing = {'status': false, 'index' : -1};  // indicate attribute edit operation


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
    $scope.newAttrib.name = ""; // reset
  };

  $scope.selectAttribute = function(idx, item) {
    console.log(idx);
    console.log(item);
    $scope.editing.status = true;
    $scope.editing.index = idx;
    $scope.newAttrib = item;
  };

  $scope.changeAttribute = function(index, item) {
    $scope.selected.attributes[index] = angular.copy(item);
    console.log($scope.selected.attributes[index]);
    console.log($scope.selected);

    //$scope.newAttrib.name = ""; // reset
    $scope.newAttrib = {'name': '', 'similarity': item.similarity, 'type': item.type}
    $scope.editing.status = false;
  };

  // specify additional parameters for attribute with interval similarity
  $scope.configIntervalAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = item;
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/interval_similarity.html',
	      controller: 'ModalIntervalInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("Interval modal closed");
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening sm modal...');
    $ctrl.open('sm');
  };

  // specify additional parameters for attribute with table similarity
  $scope.configTableAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = item;
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/table_similarity.html',
	      controller: 'ModalTableInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("Table modal closed");
	      console.log(res);
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening lg modal...');
    $ctrl.open('lg');
  };

	// specify additional parameters for attribute with enum distance similarity
  $scope.configEnumAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = item;
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/enum_distance.html',
	      controller: 'ModalEnumInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("Enum distance modal closed");
	      console.log(res);
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening lg modal...');
    $ctrl.open('lg');
  };

  // specify additional parameters for attribute with mchsherry similarity
  $scope.configMcSherryAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = item;
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/mcsherry_similarity.html',
	      controller: 'ModalMcSherryInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("Interval modal closed");
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening sm modal...');
    $ctrl.open('sm');
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
}])
.controller('ModalIntervalInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.data = angular.copy(data);
  if ($scope.data.options === undefined) { // initialise
  // option is: interval (range of possible values)
    $scope.data.options = {'interval': 100.0};
  }

  $scope.save = function() {
    //{...}
    $uibModalInstance.close($scope.data);
  };

  $scope.cancel = function() {
    //{...}
    alert("Changes will not be saved.");
    // $scope.data = angular.copy(data); // restore unchanged data
    $uibModalInstance.dismiss('cancel');
  };
}])
.controller('ModalTableInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function ($uibModalInstance, data, $scope) {
	$scope.data = angular.copy(data);
  if ($scope.data.options === undefined) { // initialise options variables if undefined
    // options are: attribute value options, symmetric or not, similarity grid values for attribute values
    $scope.data.options = {'values':[], 'is_symmetric':true, 'sim_grid':{}};
  }
	// make a temp copy of the table similarity grid
	$scope.sim_grid = angular.copy($scope.data.options.sim_grid);

	// updates the sim grid according to values
  $scope.updateGrid = function() {
    // initialise sim grid wherever it is undefined
    if ($scope.data.options.values.length > 0) {
			//console.log($scope.data.options.values);
      angular.forEach($scope.data.options.values, function(value1){
        angular.forEach($scope.data.options.values, function(value2){
	        if ($scope.sim_grid[value1] === undefined){
	          $scope.sim_grid[value1] = {};
	        }
          if ($scope.sim_grid[value1][value2] === undefined) {
            //console.log(value1 + ' ' + value2 + ' is undefined');
            if (value1 === value2) {
              $scope.sim_grid[value1][value2] = 1.0; // 1 sim for same attribute value
            } else {
              $scope.sim_grid[value1][value2] = 0.0; // 0 sim for dissimilar values
            }
          }
        });
      });
    }
  };

	// make similarity grid symmetric if using symmetric option
  $scope.makeSymmetric = function() {
    if ($scope.data.options !== undefined && $scope.data.options.is_symmetric) {
	    angular.forEach($scope.data.options.values, function(value1, key1){
	      angular.forEach($scope.data.options.values, function(value2, key2){
	        if (key2 > key1){
	          $scope.sim_grid[value1][value2] = $scope.sim_grid[value2][value1];
	        }
	      });
	    });
    }
  };

	// watch is_symmetric toggle and respond accordingly
  $scope.$watch('data.options.is_symmetric', function() {
    $scope.makeSymmetric();
  });

  // checks if a similarity grid input field should be disabled based on user options
  $scope.checkDisable = function(idx1, idx2) { // indices of the attributes
    if (idx1 === idx2)
      return true; // disable because sim of same attribute compared to itself is fixed
    if ($scope.data.options.is_symmetric && (idx1 < idx2))
      return true; // disable one entry of mirror pairs if using symmetric table
    return false;
  };

  $scope.save = function() {
    console.log($scope.sim_grid);
    //{...}
    if ($scope.data.options.values.length > 0) { // if there are values specified
      // Add the new sim values from temp copy.
      // Attribute values are used as keys to ensure that sim values are not kept for remove attribute values.
      angular.forEach($scope.data.options.values, function(value1){
        angular.forEach($scope.data.options.values, function(value2){
	        if ($scope.data.options.sim_grid[value1] === undefined){
	          $scope.data.options.sim_grid[value1] = {};
	        }
          //if ($scope.data.options.sim_grid[value1][value2] === undefined)
          if (value1 === value2) {
            $scope.data.options.sim_grid[value1][value2] = parseFloat($scope.sim_grid[value1][value2]);
          } else {
            //console.log($scope.sim_grid[value1][value2]);
            $scope.data.options.sim_grid[value1][value2] = parseFloat($scope.sim_grid[value1][value2]);
            //console.log($scope.data.options.sim_grid[value1][value2]);
          }
        });
      });
    }

    $uibModalInstance.close($scope.data);
  };

  $scope.cancel = function() {
    //{...}
    alert("Changes will not be saved.");
    //$scope.data = angular.copy(data);
    $uibModalInstance.dismiss('cancel');
  };
}])
.controller('ModalEnumInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function ($uibModalInstance, data, $scope) {
	$scope.data = angular.copy(data);
  if ($scope.data.options === undefined) { // initialise options variables if undefined
    // options are: attribute value options, symmetric or not, similarity grid values for attribute values
    $scope.data.options = {'values':[]};
  }

  $scope.save = function() {
    //{...}
    $uibModalInstance.close($scope.data);
  };

  $scope.cancel = function() {
    //{...}
    alert("Changes will not be saved.");
    //$scope.data = angular.copy(data);
    $uibModalInstance.dismiss('cancel');
  };
}])
.controller('ModalMcSherryInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.data = angular.copy(data);
  if ($scope.data.options === undefined) { // initialise
  // option is: interval (range of possible values)
    $scope.data.options = {'min': 0.0, 'max': 100.0};
  }

  $scope.save = function() {
    //{...}
    $uibModalInstance.close($scope.data);
  };

  $scope.cancel = function() {
    //{...}
    alert("Changes will not be saved.");
    //$scope.data = angular.copy(data);
    $uibModalInstance.dismiss('cancel');
  };
}]);
