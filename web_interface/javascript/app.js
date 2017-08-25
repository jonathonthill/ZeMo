
var app = angular.module("waterQuality", []);

// working with our huge data
// https://github.com/shutterstock/rickshaw/issues/421
// http://kaliatech.github.io/dygraphs-dynamiczooming-example/example1.html


var minLoop = function (arr) {
	var len = arr.length, min = Infinity;
	while (len--) {
		if (Number(arr[len]) < min) {
			min = Number(arr[len]);
		}
	}
	return min;
};

var maxLoop = function (arr) {
	var len = arr.length, max = -Infinity;
	while (len--) {
		if (Number(arr[len]) > max) {
			max = Number(arr[len]);
		}
	}
	return max;
};

app.directive("graph", ['$filter', function($filter) {

	var events = (function() {
	    var archive = {};
	    return {
			on: function(name, callback) {
				if (archive.hasOwnProperty(name)) {
					archive[name].push(callback);
				}
				else {
					archive[name] = [];
					archive[name].push(callback);
				}
			},
			trigger: function(name, obj) {
				for (var i = archive[name].length - 1; i >= 0; i--) {
					archive[name][i](obj);
				};
			}
	    }
	}());

	return {
		restrict : 'A',
		scope: {
			graph: '@',
			options: '='
		},
		link : function(scope, element, attr) {

			if (scope.options.custom) { // add custom features to the graph

				scope.options.customBars = true; // date must be in the custom data format

				// file parser - will only allow UTC time values, but parses faster
				scope.options.xValueParser = function(x) { return parseInt(x); };
				
				// date and legend date format
				scope.options.axes = { x: {
					axisLabelFormatter: function(date) {
						return $filter('date')(new Date(date), 'EEE MMM d');
					},
					valueFormatter: function(date) {
						return $filter('date')(new Date(date), 'EEE h:mm a');
					}
				}}

				// hide the labels on the x axis
				if (scope.options.custom.hideLabel) {
					scope.options.axes.x.axisLabelFormatter = function(date) {
						return '';
					}
				};

				// group the graphs with the same group name
				if (scope.options.custom.groupName) {
					var groupName = scope.options.custom.groupName;
					scope.options.zoomCallback = function(minDate, maxDate) {
						events.trigger(groupName + 'zoom', [minDate, maxDate]);
					}
					events.on(groupName + 'zoom', function(w) {
						graph.updateOptions({ dateWindow: [ w[0], w[1] ]}); // var block = false; fyi, it's also updating it's self
					});
				};

				// @todo: set up a watcher on group names and function to unsubsribe listeners

			};

			scope.options.drawCallback = function(dygraph, is_initial) { // not all the data is loaded until after it is drawn

				if (is_initial) {

					// set the y axis scale
					var rangeLow = graph.rawData_[0][1][0];
					var rangeHigh = graph.rawData_[0][1][2];

					var values = graph.rawData_.map(function(x) { return x[1][1]; });

					var min = minLoop(values);
					var max = maxLoop(values);

					min = min < rangeLow ? min : rangeLow;
					max = max > rangeHigh ? max : rangeHigh;

					var cushion = (max - min) / 3;
					var bottom = min - cushion;
					var top = max + cushion;

					graph.updateOptions({valueRange: [bottom, top]});

					// get the last value for the current value display
					scope.options.lastValue = graph.rawData_[graph.rawData_.length - 1][1][1];
					scope.$apply();
				};
			}

			var graph = new Dygraph( element[0], scope.graph, scope.options	);

		}
	}

}]);










