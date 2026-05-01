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
  var cbrRagState = {
    name: 'cbr.rag',
    templateUrl: 'cbr/views/rag.html'
  };

  $stateProvider.state(cbrState);
  $stateProvider.state(cbrRetrieveState);
  $stateProvider.state(cbrReuseState);
  $stateProvider.state(cbrReviseState);
  $stateProvider.state(cbrRetainState);
  $stateProvider.state(cbrRagState);
}])
.filter('displaySnippet', [function(){  // display snippets for long texts
  return function(input, scope, num){  // num - max no. of characters to display
    // if (typeof input != 'undefined' && scope.getDataType(input) == 'string' && scope.stringIsUrl(input)) { // returns the last part of a string if URL
    //   if (input.lastIndexOf("#") != -1)
    //     return input.substr(input.lastIndexOf("#") + 1);
    //   if (input.lastIndexOf("/") != -1)
    //     return input.substr(input.lastIndexOf("/") + 1);
    // }
    if (typeof input != 'undefined' && scope.getDataType(input) == 'string' && input.length > num) {
      return input.substr(0, num) + '...'
    }
    return input;
  }
}])
.controller('CBRCtrl', ['$scope', '$http', '$state', 'ENV_CONST', '$uibModal', function($scope, $http, $state, ENV_CONST, $uibModal ) {
  $scope.datenow = new Date();  // current date for any date field selection
  $scope.menu.active = $scope.menu.items[2]; // ui active menu tag
	  $scope.selected = {};
	  $scope.requests = { current:  { data: [], topk: 5, globalSim: "Weighted Sum", explanation: true }, previous: [], response: null };
	  $scope.rag = {
	    current: { data: [], topk: 5, include_reasoning: true, max_tokens: 1200, prompt_template: "" },
	    response: null,
	    reasoningSections: [],
	    llm: null,
	    loading: false
	  };

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
	    $scope.rag = {
	      current: { data: [], topk: 5, include_reasoning: true, max_tokens: 1200, prompt_template: $scope.getProjectRagPrompt() },
	      response: null,
	      reasoningSections: [],
	      llm: $scope.rag && $scope.rag.llm ? $scope.rag.llm : null,
	      loading: false
	    };
	  };

	  $scope.getLlmConfig = function() {
	    $http({method: 'GET', url: ENV_CONST.base_api_url + "/llm/config", headers: {"Authorization":$scope.auth.token}}).then(function(res) {
	      $scope.rag.llm = res.data;
	    }, function(err) {
	      console.log(err);
	      $scope.rag.llm = {configured: false, provider: '', model: ''};
	    });
	  };

	  $scope.getDefaultRagPrompt = function() {
	    return [
	      "You are an expert CBR assistant.",
	      "Use the retrieved cases as the main evidence and generate a new case that follows the selected project's attribute specification.",
	      "Prefer values supported by the most similar retrieved cases. Do not invent unsupported details when the evidence is insufficient.",
	      "",
	      "Query features:",
	      "{query_case}",
	      "",
	      "Retrieved cases:",
	      "{cases}",
	      "",
	      "Expected case attributes:",
	      "{attributes}",
	      "",
	      "Respond with only a valid JSON object."
	    ].join("\n");
	  };

	  $scope.resetRagPrompt = function() {
	    $scope.rag.current.prompt_template = $scope.getDefaultRagPrompt();
	  };

	  $scope.getProjectRagPrompt = function() {
	    if ($scope.selected && $scope.selected.rag && $scope.selected.rag.promptTemplate) {
	      return $scope.selected.rag.promptTemplate;
	    }
	    return $scope.getDefaultRagPrompt();
	  };

	  $scope.saveRagPromptForProject = function() {
	    var promptTemplate = $scope.rag.current.prompt_template || "";
	    if (!promptTemplate.includes("{query_case}") || !promptTemplate.includes("{cases}") || !promptTemplate.includes("{attributes}")) {
	      $scope.pop("warn", null, "Prompt template must include {query_case}, {cases}, and {attributes} before saving.");
	      return;
	    }
	    var proj = angular.copy($scope.selected);
	    proj.rag = proj.rag || {};
	    proj.rag.promptTemplate = promptTemplate;
	    delete proj.id__;

	    $http.put(ENV_CONST.base_api_url + "/project/" + $scope.selected.id__, proj, {headers: {"Authorization":$scope.auth.token}}).then(function(res) {
	      $scope.selected.rag = res.data.project.rag || proj.rag;
	      $scope.pop("success", null, "RAG prompt saved for this project.");
	    }, function(err) {
	      console.log(err);
	      $scope.pop("error", null, "Could not save RAG prompt for this project.");
	    });
	  };

	  $scope.useSavedRagPrompt = function() {
	    $scope.rag.current.prompt_template = $scope.getProjectRagPrompt();
	  };

	  $scope.runRag = function() {
	    var promptTemplate = $scope.rag.current.prompt_template || $scope.getDefaultRagPrompt();
	    if (!promptTemplate.includes("{query_case}") || !promptTemplate.includes("{cases}") || !promptTemplate.includes("{attributes}")) {
	      $scope.pop("warn", null, "Prompt template must include {query_case}, {cases}, and {attributes}.");
	      return;
	    }

	    var request = angular.copy($scope.rag.current);
	    request.project = angular.copy($scope.selected);
	    request.include_reasoning = true;
	    request.prompt_template = promptTemplate;
	    request.topk = request.topk || 5;
	    request.max_tokens = request.max_tokens || 1200;

	    $scope.rag.loading = true;
	    $http.post(ENV_CONST.base_api_url + '/rag', request, {headers:{"Authorization":$scope.auth.token}}).then(function(res) {
	      var ragResponse = res.data;
	      var generatedCase = recoverGeneratedCase(ragResponse.generatedCase);
	      var reasoning = ragResponse.reasoning || (generatedCase && generatedCase.reasoning);
	      if (generatedCase && generatedCase.generatedCase) {
	        generatedCase = generatedCase.generatedCase;
	      }

	      $scope.rag.response = ragResponse;
	      $scope.rag.reasoningSections = getReasoningSections(reasoning);
	      $scope.requests.response = {
	        recommended: generatedCase || {},
	        bestK: ragResponse.bestK || [],
	        ragTime: ragResponse.ragTime,
	        esTime: ragResponse.esTime,
	        reasoning: reasoning,
	        source: "rag"
	      };
	      $scope.rag.loading = false;
	      $scope.pop("success", null, "CBR-RAG completed.");
	    }).catch(function(err) {
	      console.log(err);
	      $scope.rag.loading = false;
	      $scope.pop("error", null, "An error occurred while running CBR-RAG.");
	    });
	  };

	  $scope.reviseRagCase = function() {
	    if (!$scope.requests.response || !$scope.requests.response.recommended) {
	      $scope.pop("warn", null, "Run CBR-RAG before revising a generated case.");
	      return;
	    }
	    $scope.reviseCase();
	  };

	  function recoverGeneratedCase(generatedCase) {
	    if (!generatedCase || !generatedCase._error || !generatedCase.raw_response) {
	      return generatedCase;
	    }
	    var parsed = parseLlmJsonLike(generatedCase.raw_response);
	    return parsed || generatedCase;
	  }

	  function parseLlmJsonLike(value) {
	    if (typeof value !== "string") {
	      return null;
	    }
	    var cleaned = value.trim().replace(/^```(?:json)?\\s*/i, "").replace(/\\s*```$/i, "").trim();
	    var candidates = [cleaned];
	    var fencedMatch = value.match(/```(?:json)?\\s*([\\s\\S]*?)```/i);
	    if (fencedMatch && fencedMatch[1]) {
	      candidates.push(fencedMatch[1].trim());
	    }
	    var extracted = extractFirstJsonObject(cleaned);
	    if (extracted) {
	      candidates.push(extracted);
	    }
	    for (var i = 0; i < candidates.length; i++) {
	      try {
	        var parsed = JSON.parse(candidates[i]);
	        return parsed && typeof parsed === "object" ? parsed : null;
	      } catch (_err) {}
	    }
	    return null;
	  }

	  function extractFirstJsonObject(value) {
	    var start = value.indexOf("{");
	    if (start < 0) {
	      return null;
	    }
	    var depth = 0;
	    var inString = false;
	    var escaped = false;
	    for (var index = start; index < value.length; index += 1) {
	      var char = value[index];
	      if (escaped) {
	        escaped = false;
	        continue;
	      }
	      if (char === "\\\\") {
	        escaped = true;
	        continue;
	      }
	      if (char === '"') {
	        inString = !inString;
	        continue;
	      }
	      if (inString) {
	        continue;
	      }
	      if (char === "{") {
	        depth += 1;
	      }
	      if (char === "}") {
	        depth -= 1;
	        if (depth === 0) {
	          return value.slice(start, index + 1);
	        }
	      }
	    }
	    return null;
	  }

	  function getReasoningSections(reasoning) {
	    if (!reasoning) {
	      return [];
	    }
	    if (typeof reasoning === "string") {
	      var parsed = parseLlmJsonLike(reasoning);
	      if (parsed) {
	        return getReasoningSections(parsed);
	      }
	      return [{key: "Reasoning", value: reasoning, isArray: false, isObject: false}];
	    }
	    if (typeof reasoning !== "object") {
	      return [{key: "Reasoning", value: String(reasoning), isArray: false, isObject: false}];
	    }
	    return Object.keys(reasoning).map(function(key) {
	      var value = reasoning[key];
	      return {
	        key: key.replace(/_/g, " "),
	        value: Array.isArray(value) || typeof value === "object" ? JSON.stringify(value, null, 2) : value,
	        isArray: Array.isArray(value),
	        isObject: typeof value === "object"
	      };
	    });
	  }

  // retrieves cases from the casebase using specified request features
  $scope.retrieveCases = function() {
    $scope.requests.current.project = angular.copy($scope.selected);

    // console.log("Current ", $scope.requests.current); // array attributes: name, value, weight, unknown, strategy (if unknown)
	    $http.post(ENV_CONST.base_api_url + '/retrieve', $scope.requests.current, {headers:{"Authorization":$scope.auth.token}}).then(function(res) {
	      $scope.requests.response = res.data;
	      $scope.requests.response.source = "retrieve";
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
      if ((value.type == "Array") && newCase.data[value.name] != null && newCase.data[value.name] != "") {
        newCase.data[value.name] = newCase.data[value.name].split(",").map(item=>item.trim());
        if (value.type == "Integer") {
          newCase.data[value.name] = newCase.data[value.name].map(function (el) { return parseInt(el); });
        } else if (value.type == "Float") {
          newCase.data[value.name] = newCase.data[value.name].map(function (el) { return parseFloat(el); });
        }
      // console.log("newCase",newCase);
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
	    $state.transitionTo($scope.requests.response.source == "rag" ? 'cbr.rag' : 'cbr.reuse');
	  };

  //Export the results of the best k cases to a csv file
  $scope.exportResults = function(){

    // Get the attribute names for the header
    let headers = $scope.selected.attributes.map(function (el) { return el.name; });
    var replacer = function(key, value) { return value === null ? '' : value }

    var csv = $scope.requests.response.bestK.map(function(row){
      return headers.map(function(fieldName){
        return JSON.stringify(row[fieldName], replacer)
      }).join(',')
    });

    csv.unshift(headers.join(',')); // add header column
    csv = csv.join('\r\n');

    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement("a");
    var url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "results.csv");
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    $scope.pop("success", null, "Downloading cases as CSV");
  };

  // Check if data type can be used as a filter
  $scope.getIsFilterOptions = function(type) {
    if (typeof type != 'undefined' && type != null) {
      var res = $scope.globalConfig.attributeOptions.find(obj => {
        return obj.type === type
      });
      return res.filterOptions;
    }
    return false;
  };

  // checks if string is a url
  $scope.stringIsUrl = function(str) {
    let url;
    try {
      url = new URL(str);
    } catch (_) {
      return false;
    }
    return url.protocol === "http:" || url.protocol === "https:";
  }

  $scope.reusePlot = function() {
    updatePlotType('scatter');
    
    // add event listeners to buttons
    document.getElementById('scatter-button').addEventListener('click', () => updatePlotType('scatter'));
    document.getElementById('bar-button').addEventListener('click', () => updatePlotType('bar'));
    document.getElementById('parallel-button').addEventListener('click', () => updatePlotType('parcoords'));
  };
  
  function getTraces(bestK, type) {
    return bestK.map((value, index) => {
      const { match_explanation, score__ } = value;
      const attributes = match_explanation.map(({ similarity, field }) => field);
      attributes.push("<b>Global Similarity</b>");
      const scores = match_explanation.map(({ similarity }) => similarity);
      scores.push(score__);
      return {
        x: attributes,
        y: scores,
        type: type,
        line: {shape: 'hvh'},
        name: `Case ${index + 1}`
      };
    });
  }
  
  function updatePlotType(type) {
    const plotlyGraph = document.getElementById('plotly-graph');
    const plotData = plotlyGraph.data;
    const { bestK } = $scope.requests.response;
    const updatedData = getTraces(bestK.slice(0, 5), type);
  
    const layout = {
      title: {
        text: type === 'scatter' ? 'Scatter Plot' : 'Bar Plot',
        font: {
          family: 'Arial',
          size: 24,
          color: 'rgb(120,120,120)'
        }
      },
      paper_bgcolor: 'rgb(243, 243, 243)',
      plot_bgcolor: 'rgb(243, 243, 243)',
      margin: {
        l: 100,
        r: 100,
        t: 100,
        b: 100
      },
      showlegend: true
    };
  
    if (type === 'parcoords') {
      const numDimensions = plotData[0].x.length;
      const dimensions = plotData[0].x.map((attribute, index) => {
        const isLastDimension = index === numDimensions - 1;
        const label = attribute.replace('<b>', '').replace('</b>', '');
        const range = isLastDimension ? [0, numDimensions - 1] : [0, 1];
        const values = plotData.map(trace => trace.y[index]);
        return { label, range, values };
      });
  
      const trace = {
        type: 'parcoords',
        line: {
          color: plotData.map(trace => trace.y[numDimensions - 1]),
          showscale: true,
          reversescale: true,
          colorscale: 'Jet',
          cmin: 0,
          cmax: numDimensions - 1,
        },
        dimensions: dimensions,
        name: 'Series 1'
      };
  
      layout.title.text = 'Parallel Coordinates Plot';
      layout.legend = {
        orientation: 'h',
        yanchor: 'bottom',
        y: 1.02,
        xanchor: 'right',
        x: 1
      };
  
      Plotly.newPlot(plotlyGraph, [trace], layout);
    } else {
      layout.legend = {};
  
      layout.xaxis = {
        title: {
          text: 'Attributes',
          font: {
            family: 'Arial',
            size: 18,
            color: 'rgb(120,120,120)'
          }
        }
      };
      layout.yaxis = {
        title: {
          text: 'Similarity',
          font: {
            family: 'Arial',
            size: 18,
            color: 'rgb(120,120,120)'
          }
        }
      };
  
      Plotly.newPlot(plotlyGraph, updatedData, layout);
    }
  }

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
	  $scope.getLlmConfig();
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
}])
.directive('truncateJson', function () {
  return {
    restrict: 'A',
    scope: {
      jsonData: '=truncateJson',
    },
    link: function (scope, element) {
      if (!scope.jsonData) {
        return;
      }

      const jsonDataStr = JSON.stringify(scope.jsonData, null, 2);

      if (jsonDataStr.length < 50) {
        element.html(jsonDataStr);
        return;
      }
      const truncatedJsonDataStr = jsonDataStr.slice(0, 50) + '...';
      element.html(truncatedJsonDataStr);
      element.css('cursor', 'pointer');

      let isTruncated = true;
      element.on('click', function () {
        if (isTruncated) {
          element.html(jsonDataStr);
        } else {
          element.html(truncatedJsonDataStr);
        }
        isTruncated = !isTruncated;
      });
    },
  };
});
