'use strict';

angular.module('cloodApp.projects', [])
.config(['$stateProvider', function($stateProvider) {
  var projectsState = {
    name: 'projects',
    url: '/projects',
    templateUrl: 'projects/projects.html',
    controller: 'ProjectCtrl'
  };
  $stateProvider.state(projectsState);
}])
.controller('ProjectCtrl', ['$scope', '$http', 'Project', 'ENV_CONST', function($scope, $http, Project, ENV_CONST) {
  $scope.menu.active = $scope.menu.items[0]; // ui active menu tag
  $scope.projects = [];
  $scope.newProj = null; // new project to be saved

  if (typeof ENV_CONST.base_api_url == 'undefined' || ENV_CONST.base_api_url == '') {
    $scope.pop("warn", null, "The root API to the serverless functions is not set. You can set this up in env.js");
  }

  $scope.getAllProjects = function() {
    $http({method: 'GET', url: ENV_CONST.base_api_url + "/project", headers: {"Authorization":$scope.auth.token}}).then(function(res) {
      $scope.projects = res.data;
      console.log(res.data);
    });
  };

  // Creates new project
  $scope.newProject = function() {
    var item = angular.copy($scope.newProj);
    var proj = new Project($scope.newProj);
    $http.post(ENV_CONST.base_api_url + "/project/", proj, {headers:{"Authorization":$scope.auth.token}}).then(function(res){
      console.log("res",res);
      item.id__ = res.data.project.id__;
      $scope.projects.push(item); // refresh list
      $scope.pop("success", null, "New project save.");
      $scope.newProj = null; // reset form fields
    }, function(err){
      console.log(err);
      $scope.pop("error", null, "Error saving new project.");
    });
  };

  $scope.viewProject = function(item) {
    $scope.newProj = item;
  };

  $scope.resetViewProject = function() {
    $scope.getAllProjects();
    $scope.newProj = null;
  };

  // Updates a project
  $scope.updateProject = function() {
    var proj = angular.copy($scope.newProj);
    delete proj.id__;
    $http.put(ENV_CONST.base_api_url + "/project/" + $scope.newProj.id__, proj, {headers: {"Authorization":$scope.auth.token}}).then(function(res){
      console.log("res",res);
      const index = $scope.projects.findIndex(p => p.id__ === res.data.project.id__);
      $scope.projects[index] = $scope.newProj;
      console.log(res);
      $scope.pop("success", null, "Project detail updated.");
      $scope.newProj = null; // reset
    }, function(err){
      console.log(err);
      $scope.pop("error", null, "Error updating project detail.");
    });
  };

  // Deletes a project
  $scope.deleteProject = function(item) {
    $http({method: 'DELETE', url: ENV_CONST.base_api_url + "/project/" + item.id__, headers: {"Authorization":$scope.auth.token}}).then(function(){
      $scope.projects = $scope.projects.filter(function(el) { return el.id__ != item.id__; });
      $scope.pop("success", null, "Project deleted!");
      $scope.newProj = null; // cancel any selection on ui
    }, function(err){
      console.log(err);
      $scope.pop("error", null, "Item was not deleted as something went wrong.")
    })
  };

  // Export Project
  $scope.exportProject = function(item) {
    let itemJSON = JSON.stringify(item);
    let dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(itemJSON);
    let fileName = "clood-"+item.id__+'.json';

    let downloadLink = document.createElement('a');
    downloadLink.setAttribute('href', dataUri);
    downloadLink.setAttribute('download', fileName);
    downloadLink.click();

    $scope.pop("success", null, "Project Exporting!");
  };

  // Import Project from File
  $scope.importProject = function () {
    var files = document.getElementById('importFile').files;
    if (files.length <= 0) {
        $scope.pop("error", null, "No file selected.")
        return false;
    }
    document.getElementById("importBtn").disabled = true;
    var fr = new FileReader();

    fr.onload = function (e) {
        var importedJSON = JSON.parse(e.target.result);

        // Create a New Project
        var importedProj = new Project(
            {
                description: importedJSON.description,
                name: importedJSON.name,
                retainDuplicateCases: importedJSON.retainDuplicateCases ?? false,
                attributes: importedJSON.attributes
            }
        );
        console.log(importedProj)
        $http.post(ENV_CONST.base_api_url + "/project/", importedProj, {headers:{"Authorization":$scope.auth.token}}).then(function(res){
          $scope.pop("success", null, "Succesfully imported project " + importedJSON.name + " !");
          $scope.projects.push(res.data.project); // refresh list
          $scope.newProj = null;
          document.getElementById("importBtn").disabled = false;
          $('#importModal').modal('hide');
        }, function (err) {
            console.log(err);
            $scope.pop("error", null, "Error importing project.");
        });
    }
    fr.readAsText(files.item(0));
  };

  $scope.getAllProjects();

}]);
