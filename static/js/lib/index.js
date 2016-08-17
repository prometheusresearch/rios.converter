/**
 * @copyright 2016, Prometheus Research, LLC
 */

'use strict';

// Include jQuery for bootstrap
var $ = global.jQuery = require('jquery');

// Include bootstrap JS deps
require('bootstrap')

// Select all elements with data-toggle="tooltips" in the document
$(function () {
  $('[data-toggle="tooltip"]').tooltip();
});
