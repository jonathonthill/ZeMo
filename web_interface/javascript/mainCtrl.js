
app.controller('mainCtrl', ['$scope', function($scope) {

	$scope.tp_options = {
		ylabel: 'Temperature (&deg;C)',
		labels: ['Date','Temperature'],
		color: '#FECB2E',
		axisLineColor: 'rgba(0, 0, 0, 0.7)',
		custom: {
			hideLabel: true,
			groupName: 'rack'
		},
		lastValue: 0
	}

	$scope.ph_options = {
		ylabel: 'pH',
		labels: ['Date','pH'],
		color: '#ABC356',
		axisLineColor: 'rgba(0, 0, 0, 0.7)',
		custom: {
			hideLabel: true,
			groupName: 'rack'
		},
		lastValue: 0
	}

	$scope.do_options = {
		ylabel: 'Disolved Oxygen (ppm)',
		labels: ['Date','Disolved Oxygen'],
		color: '#0D67AC',
		axisLineColor: 'rgba(0, 0, 0, 0.7)',
		custom: {
			hideLabel: true,
			groupName: 'rack'
		},
		lastValue: 0
	}

	$scope.cd_options = {
		ylabel: 'Conductivity (Î¼S)',
		labels: ['Date','Conductivity'],
		color: '#775E85',
		axisLineColor: 'rgba(0, 0, 0, 0.7)',
		custom: {
			groupName: 'rack'
		},
		lastValue: 0
		// valueRange: [20,40],
	}

	console.log($scope.cd_options);

}]);





