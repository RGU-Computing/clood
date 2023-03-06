'use strict';

angular.module('cloodApp.env', [])
.constant('ENV_CONST', {
  // Set the root API URL below without a trailing slash and change file name to env.js
  // Supports the docker version: Change in Production
  base_api_url: 'http://localhost:3000/dev'
});
