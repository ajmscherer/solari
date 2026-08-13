'use strict';

const exec = require('child_process').exec;

// Volumio does not put /volumio/node_modules on NODE_PATH for data plugins.
let libQ;
try {
  libQ = require('kew');
} catch (e) {
  libQ = require('/volumio/node_modules/kew');
}

module.exports = ControllerSolariDisplay;

function ControllerSolariDisplay (context) {
  this.context = context;
  this.commandRouter = this.context.coreCommand;
  this.logger = this.context.logger;
}

ControllerSolariDisplay.prototype.onVolumioStart = function () {
  return libQ.resolve();
};

ControllerSolariDisplay.prototype.onStart = function () {
  this.addToBrowseSources();
  return libQ.resolve();
};

ControllerSolariDisplay.prototype.onStop = function () {
  return libQ.resolve();
};

ControllerSolariDisplay.prototype.onRestart = function () {
  return libQ.resolve();
};

ControllerSolariDisplay.prototype.getConfigurationFiles = function () {
  return [];
};

ControllerSolariDisplay.prototype.addToBrowseSources = function () {
  this.commandRouter.volumioAddToBrowseSources({
    name: 'Solari',
    uri: 'solari',
    plugin_type: 'music_service',
    plugin_name: 'solari_display',
    icon: 'fa-th'
  });
};

ControllerSolariDisplay.prototype.handleBrowseUri = function (curUri) {
  const defer = libQ.defer();
  const self = this;
  exec('/home/volumio/solari/tivoli/switch-to-solari.sh', function (error) {
    if (error) {
      self.logger.error('solari_display: ' + error);
      self.commandRouter.pushToastMessage('error', 'Solari', 'Could not switch display');
    } else {
      self.commandRouter.pushToastMessage('success', 'Solari', 'Switching to Solari');
    }
    defer.resolve({
      navigation: {
        prev: { uri: '/' },
        lists: [{
          title: 'Solari',
          availableListViews: ['grid', 'list'],
          items: [{
            service: 'solari_display',
            type: 'item-no-menu',
            title: 'Show Solari board',
            icon: 'fa fa-th',
            uri: 'solari'
          }]
        }]
      }
    });
  });
  return defer.promise;
};
