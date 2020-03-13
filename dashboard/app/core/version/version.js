'use strict';

angular.module('cloodApp.version', [
  'cloodApp.version.interpolate-filter',
  'cloodApp.version.version-directive'
])

.value('version', '0.1');
