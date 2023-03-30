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
  var configAddCaseState = {
    name: 'config.add_case',
    templateUrl: 'config/views/add_case.html'
  };
  $stateProvider.state(configState);
  $stateProvider.state(configAttributesState);
  $stateProvider.state(configAddDataState);
  $stateProvider.state(configAddCaseState);
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
  $scope.newCase = {'data':{}, 'project':{}};


  // Get all projects
  $scope.getAllProjects = function() {
    $http({method: 'GET', url: ENV_CONST.base_api_url + "/project", headers: {"Authorization":$scope.auth.token}}).then(function(res){
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
      // Check to see if the attribute should have any options - don't really like hardcoding it like this:P
      item.options = {};
      if(item.similarity == 'Interval' || item.similarity == 'McSherry Less' || item.similarity == 'McSherry More' || item.similarity == 'INRECA Less' || item.similarity == 'INRECA More') {
        item.options.max = 100;
        item.options.min = 1;
        item.options.jump = 1;
      } else if(item.similarity == 'Nearest Number') {
        item.options.nscale = 1;
        item.options.ndecay = 0.9;
      } else if(item.similarity == 'Nearest Date') {
        item.options.dscale = "1d";
        item.options.ddecay = 0.9;
      }
      console.log("item2",item);
      $scope.selected.attributes.push(angular.copy(item)); // add to the selected project's attributes
    } else {
      console.log('Cannot have duplicate attribute names');
    }
    $scope.newAttrib.name = ""; // reset
  };

  $scope.selectAttribute = function(idx, item) {
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
	      console.log("McSherry modal closed");
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening sm modal...');
    $ctrl.open('sm');
  };

  // specify additional parameters for attribute with INRECA similarity
  $scope.configInrecaAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = item;
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/inreca_similarity.html',
	      controller: 'ModalInrecaInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("INRECA modal closed");
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening sm modal...');
    $ctrl.open('sm');
  };

  // specify additional parameters for attribute with ontology-based similarity
  $scope.configOntologyAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = [item, $scope.selected];
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/ontology_similarity.html',
	      controller: 'ModalOntologyInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("Ontology modal closed");
//	      res.options.id = $scope.selected.id__ + "_ontology_" + item.name.toLowerCase();
	      console.log(res);
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening sm modal...');
    $ctrl.open('lg');
  };

  // specify additional parameters for attribute with Nearest Number similarity
  $scope.configDecayFunctionAttribute = function(idx, item) {
    // for modals
    var $ctrl = this;
	  $ctrl.data = item;
	  $ctrl.open = function (size) {
	    var modalInstance = $uibModal.open({
	      animation: true,
	      backdrop: false,  // prevents closing modal by clicking outside it
	      ariaLabelledBy: 'modal-title',
	      ariaDescribedBy: 'modal-body',
	      templateUrl: 'config/views/modalviews/nearestnumber_similarity.html',
	      controller: 'ModalNearestNumberInstanceCtrl',
	      controllerAs: '$ctrl',
	      size: size,
	      resolve: {
	        data: function () {
	          return $ctrl.data;
	        }
	      }
	    });

	    modalInstance.result.then(function (res) {
	      console.log("Decay function modal closed");
	      $scope.changeAttribute(idx, res);
	    });
	  };
    console.log('opening sm modal...');
    $ctrl.open('lg');
  };

  $scope.simListPopup = function(info) {
    var $ctrl = this;
    $ctrl.data = info
    $ctrl.open = function (size) {
      var modalInstance = $uibModal.open({
        animation: true,
        backdrop: true,  // prevents closing modal by clicking outside it
        ariaLabelledBy: 'modal-title',
        ariaDescribedBy: 'modal-body',
        templateUrl: 'config/views/modalviews/similarity_list.html',
        controller: 'ModalSimListInstanceCtrl',
        controllerAs: '$ctrl',
        size: 'lg',
        resolve: {
          data: function () {
            return $ctrl.data
          }
        }
      })
      modalInstance.result.then(function (res) {
        console.log("Similarity list modal closed");
      });
    };
    $ctrl.open('lg');
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
    $http.put(ENV_CONST.base_api_url + "/project/" + projId, proj, {headers: {"Authorization":$scope.auth.token}}).then(
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
    $http.put(ENV_CONST.base_api_url + "/project" + "/mapping/" + $scope.selected.id__, {headers: {"Authorization":$scope.auth.token}}).then(function(res) {
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

  // export csv template
  $scope.exportTemplate = function() {
    //Retrieve and format attributes of the current project
    let itemJSON = ""
    $scope.selected.attributes.forEach(function(value,index){
      index == 0 ? itemJSON += value.name : itemJSON += ","+value.name
    });
    let dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(itemJSON);
    let fileName = "clood-"+$scope.selected.id__+'-template.csv';

    let downloadLink = document.createElement('a');
    downloadLink.setAttribute('href', dataUri);
    downloadLink.setAttribute('download', fileName);
    downloadLink.click();

    $scope.pop("success", null, "Downloading CSV template");
  };


  // Need to create a new csv parser using manual rules and not papa parse
  $scope.parseFile = function(file) {
    // open file
    var reader = new FileReader();
    reader.readAsText(file);
    reader.onload = function(event) {
      var lines = event.target.result.split("\n");
      //Get an array of the column headers and data rows
      var columnHeads = lines[0].split(",");
      var data = lines.slice(1,lines.length);

      // Check number and name of column headers against the current project attributes
      var projectAttributes = $scope.selected.attributes.map(function (el) { return el.name; });
      var columnHeaders = columnHeads.map(function (el) { return el.trim(); });
      if (columnHeaders.length != projectAttributes.length) {
        $scope.displayWarning = "The number of columns in the file does not match the number of attributes for this project.";
        return;
      }
      else if (!columnHeaders.every(function (el) { return projectAttributes.includes(el); })) {
        $scope.displayWarning = "The column headers in the file do not match the attributes for this project. The following attributes are wrong: " + columnHeaders.filter(function (el) { return !projectAttributes.includes(el); }).join(", ") + ".";
        return;
      }

      var formattedData = [];
      // Check each line of data for the correct number of columns
      for (var i = 0; i < data.length; i++) {
        // Create an array of proper comma locations
        var commas = [];
        for (var j = 0; j < data[i].length; j++) {
          if (data[i][j] == ",") {
            //calculate the number of double quotes, and parentheses before the comma
            let numQuotes = 0;
            let numCurlyBrace = 0;
            let numSquareBrace = 0;

            for (let k = 0; k < j; k++) {
              switch (data[i][k]) {
                case "\"":
                  numQuotes++;
                  break;
                case "{":
                  numCurlyBrace++;
                  break;
                case "}":
                  numCurlyBrace--;
                  break;
                case "[":
                  numSquareBrace++;
                  break;
                case "]":
                  numSquareBrace--;
                  break;
              }
            }

            // If the number of double quotes is even, and the number of parentheses is 0, then the comma is a proper comma
            if (numQuotes % 2 == 0 && numCurlyBrace == 0 && numSquareBrace == 0) {
              console.log("proper comma at " + j);
              commas.push(j);
            }
          }
        }

        // If the number of commas found is not equal to the number of column headers - 1, then there is an error
        if (commas.length != columnHeaders.length - 1) {
          $scope.displayWarning = "There is an error in the data on line " + (i+1) + ". Number of values does not match number of column headers.";
          return;
        }

        // If there are no errors, then begin formatting the data
        $scope.newCasebase.columnHeads = columnHeaders;

        let obj = {};
        function getTempString(data, i, commas, j) {
          if (j === 0) {
            return data[i].slice(0, commas[j]);
          } else if (j === commas.length) {
            return data[i].slice(commas[j - 1] + 1);
          } else {
            return data[i].slice(commas[j - 1] + 1, commas[j]);
          }
        }

        columnHeaders.forEach((header, j) => {
          const tempString = getTempString(data, i, commas, j);
          // Check if tempString has a value, if not, set it to null
          if (tempString.trim() === "") {
            obj[header] = null;
          }
          else {
            obj[header] = JSON.parse(tempString.trim());
          }
        });

        formattedData.push(obj);
        $scope.newCasebase.data = formattedData;
      }
    };
    reader.onerror = function() {
      $scope.displayWarning = "Unable to read " + file.fileName;
    };
  };


  $scope.readFile = function(event) {
    var files = event.target.files;
    console.log(files);
    $scope.displayWarning = "";
    $scope.parseFile(files[0]);
  };

  // Save casebase
  $scope.saveCasebase = function() {
    console.log($scope.newCasebase);
    
    $http.post(ENV_CONST.base_api_url + "/case/" + $scope.selected.id__ + "/list", $scope.newCasebase.data, {headers: {"Authorization":$scope.auth.token}})
        .then(function(res) {
          console.log(res);
          $scope.newCasebase = {'data':[], 'columnHeads':[], 'preview':false}; // reset
          $scope.selected.hasCasebase = true;
          $scope.pop("success", null, "Data added.");
          // Clear file input
          document.getElementById("formControlFile1").value = "";
        })
        .catch(function(err) {
          console.log(err);
          $scope.pop("error", null, "An error occurred while trying to save data.");
        });
  };

   // saves a new case to the casebase
   $scope.saveCase = function() {
    $scope.newCase.project = $scope.selected;
    angular.forEach($scope.newCase.project.attributes, function(value, key) {
      if(value.type == "Object" && $scope.newCase.data[value.name] != null && $scope.newCase.data[value.name] != ""){
        $scope.newCase.data[value.name] = JSON.parse($scope.newCase.data[value.name]);
      }
    });

    $http.post(ENV_CONST.base_api_url + '/retain', $scope.newCase, {headers:{"Authorization":$scope.auth.token}}).then(function(res) {
      console.log(res.data);
      $scope.pop("success", null, "New case added.");
      $scope.newCase = {'data':{}, 'project':{}};
    }).catch(function(err) {
      console.log(err);
      $scope.pop("error", null, "Case added was not added. Duplicate cases are rejected when not allowing duplicates.");
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
  console.log("sim_grid: " + JSON.stringify($scope.data.options));
	// updates the sim grid according to values
  $scope.updateGrid = function() {
    // initialise sim grid wherever it is undefined
    if ($scope.data.options.values !== undefined && $scope.data.options.values.length > 0) {
			//console.log($scope.data.options.values);
      angular.forEach($scope.data.options.values, function(value1){
        angular.forEach($scope.data.options.values, function(value2){
          console.log("sim_grid: " + JSON.stringify($scope.sim_grid));
	        if ($scope.sim_grid === undefined){
	          $scope.sim_grid = {};
	        }
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
    console.log($scope.data.options);
    //{...}
    if ($scope.data.options.values.length > 0) { // if there are values specified
      if (typeof $scope.data.options.sim_grid == 'undefined') {
        console.log('sim_grid is undefined');
        $scope.data.options.sim_grid = {}
      }
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
    // option is the attribute value options
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
    // options initialised with default values
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
}])
.controller('ModalInrecaInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.data = angular.copy(data);
  if ($scope.data.options === undefined) { // initialise
    // options initialised with default values
    $scope.data.options = {'jump': 1.0, 'max': 100.0};
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
.controller('ModalOntologyInstanceCtrl', ['$uibModalInstance', 'data', '$scope', '$http', 'ENV_CONST', function($uibModalInstance, data, $scope, $http, ENV_CONST) {
  $scope.data = angular.copy(data[0]);
  $scope.project_has_casebase = data[1]['hasCasebase'];
  var proj_id = data[1]['id__'];
  if ($scope.data.options === undefined) { // initialise
    $scope.data.options = {'name': $scope.data.name.toLowerCase(), 'sources': []};
  }

  // add an ontology source to attribute options
  $scope.addSource = function(item) {
    $scope.data.options.sources.push(angular.copy(item));
    $scope.newSource = {}; //reset
  };

  // Removes attribute from project attributes list if it exists
  $scope.removeSource = function(item) {
    for (var i = 0; i < $scope.data.options.sources.length; i++) {
      if ($scope.data.options.sources[i].source === item.source) {
        $scope.data.options.sources.splice(i,1);
        break;
      }
    }
  };

//	$scope.ontology_relatedness_created = false;
//  $scope.checkStatus = function() {
//    //generates pairwise similarity measures for all the concepts in the ontology.
//    //can be a lengthy operation for mid to large ontologies.
//    $http.get(ENV_CONST.base_api_url + '/ontology_sim/' + $scope.data.options.id)
//      .then(function(res) {
//          $scope.ontology_relatedness_created = true;
//          console.log(res);
//        })
//        .catch(function(err) {
//          console.log(err);
//        });
//  };

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
.controller('ModalNearestNumberInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.data = angular.copy(data);
  console.log($scope.data);
  if ($scope.data.options === undefined) { // initialise
    // options initialised with default values
    if ($scope.data["similarity"] == "Nearest Number")
      $scope.data.options = {'nscale': 1, 'ndecay': 0.999};
    if ($scope.data["similarity"] == "Nearest Date")
      $scope.data.options = {'dscale': '365d', 'ddecay': 0.999};
    if ($scope.data["similarity"] == "Nearest Location")
      $scope.data.options = {'lscale': '10km', 'ldecay': 0.999};
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
.controller('ModalSimListInstanceCtrl', ['$uibModalInstance', 'data', '$scope', function($uibModalInstance, data, $scope) {
  $scope.save = function() {
    $uibModalInstance.close();
  };

  $scope.cancel = function() {
    $uibModalInstance.dismiss('cancel');
  };
}]);
