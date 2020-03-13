'use strict';

describe('cloodApp.version module', function() {
  beforeEach(module('cloodApp.version'));

  describe('version service', function() {
    it('should return current version', inject(function(version) {
      expect(version).toEqual('0.1');
    }));
  });
});
