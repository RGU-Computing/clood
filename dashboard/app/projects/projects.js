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
.factory('Project', ['$resource', 'ENV_CONST', function($resource, ENV_CONST) {
  return $resource(ENV_CONST.base_api_url + "/project" + '/:id', null, {
    'update': { method: 'PUT'}
  });
}])
.controller('ProjectCtrl', ['$scope', '$http', 'Project', 'ENV_CONST', function($scope, $http, Project, ENV_CONST) {
  $scope.menu.active = $scope.menu.items[0]; // ui active menu tag
  $scope.projects = [];
  $scope.newProj = null; // new project to be saved

  if (typeof ENV_CONST.base_api_url == 'undefined' || ENV_CONST.base_api_url == '') {
    $scope.pop("warn", null, "The root API to the serverless functions is not set. You can set this up in env.js");
  }

  $scope.getAllProjects = function() {
    $http.get(ENV_CONST.base_api_url + "/project").then(function(res) {
      $scope.projects = res.data;
      console.log(res.data);
    });
  };

  // Creates new project
  $scope.newProject = function() {
    var item = angular.copy($scope.newProj);
    var proj = new Project($scope.newProj);
    proj.$save({}, function(res){
      console.log(res);
      item.id__ = res._id;
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
    Project.update({ id: $scope.newProj.id__ }, proj).$promise.then(function(res){
      const index = $scope.projects.findIndex(p => p.id__ === res._id);
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
    Project.delete({
      id: item.id__
    }).$promise.then(function(){
      $scope.projects = $scope.projects.filter(function(el) { return el.id__ != item.id__; });
      $scope.pop("success", null, "Project deleted!");
      $scope.newProj = null; // cancel any selection on ui
    }, function(err){
      console.log(err);
      $scope.pop("error", null, "Item was not deleted as something went wrong.")
    })
  };


  // use.load().then(model => {
  //   // Embed an array of sentences.
  //   const sentences = [
  //     'Hello.',
  //     'How are you?'
  //   ];
  //   model.embed(sentences).then(embeddings => {
  //     // `embeddings` is a 2D tensor consisting of the 512-dimensional embeddings for each sentence.
  //     // So in this example `embeddings` has the shape [2, 512].
  //     // embeddings.print(true /* verbose */);
  //     embeddings.array().then(function(d) {
  //       console.log(JSON.stringify(d));
  //     });
  //   });
  // });

  $scope.getAllProjects();

}]);
