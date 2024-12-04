console.log('Address.js loaded');

let map;
let marker;
let autocomplete;

function initMap() {
    console.log('Initializing map...');
    
    // Check if the map div exists
    const mapDiv = document.getElementById('map');
    if (!mapDiv) {
        console.error('Map container not found');
        return;
    }
    
    try {
        // Default to South Africa
        const defaultLocation = { lat: -30.5595, lng: 22.9375 };
        
        // Initialize the map
        map = new google.maps.Map(mapDiv, {
            center: defaultLocation,
            zoom: 5,
            mapTypeControl: true,
            streetViewControl: true,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        });

        console.log('Map initialized');

        // Initialize the marker
        marker = new google.maps.Marker({
            map: map,
            draggable: true,
            animation: google.maps.Animation.DROP
        });

        // Initialize autocomplete
        initAutocomplete();

    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

function initAutocomplete() {
    console.log('Initializing autocomplete...');
    
    const input = document.getElementById('street_address');
    if (!input) {
        console.error('Street address input not found!');
        return;
    }

    // Create the autocomplete object
    autocomplete = new google.maps.places.Autocomplete(input, {
        types: ['address'],
        componentRestrictions: { country: ['za'] },
        fields: ['address_components', 'geometry', 'formatted_address']
    });

    // Bind autocomplete to the map
    autocomplete.bindTo('bounds', map);

    // Handle place selection
    autocomplete.addListener('place_changed', function() {
        const place = autocomplete.getPlace();
        console.log('Place selected:', place);

        if (!place.geometry || !place.geometry.location) {
            alert('No details available for this place');
            return;
        }

        updateMapLocation(place.geometry.location);
        fillInAddress(place);
    });
}

function updateMapLocation(location) {
    map.setCenter(location);
    map.setZoom(17);
    marker.setPosition(location);
    marker.setVisible(true);
    updateFormCoordinates(location);
}

function updateFormCoordinates(location) {
    document.getElementById('latitude').value = location.lat();
    document.getElementById('longitude').value = location.lng();
}

function fillInAddress(place) {
    clearFormFields();

    for (const component of place.address_components) {
        const componentType = component.types[0];
        
        switch (componentType) {
            case 'street_number':
                document.getElementById('door_number').value = component.long_name;
                break;
            case 'route':
                document.getElementById('street_address').value = component.long_name;
                break;
            case 'sublocality':
            case 'sublocality_level_1':
                document.getElementById('suburb').value = component.long_name;
                break;
            case 'locality':
                document.getElementById('city').value = component.long_name;
                break;
            case 'administrative_area_level_1':
                selectOptionByText('state', component.long_name);
                break;
            case 'country':
                selectOptionByText('country', component.long_name);
                break;
        }
    }

    // Set the full formatted address
    document.getElementById('street_address').value = place.formatted_address;
}

function selectOptionByText(selectId, text) {
    const selectElement = document.getElementById(selectId);
    if (selectElement) {
        for (let i = 0; i < selectElement.options.length; i++) {
            if (selectElement.options[i].text.toLowerCase() === text.toLowerCase()) {
                selectElement.value = selectElement.options[i].value;
                break;
            }
        }
    }
}

function clearFormFields() {
    const fields = ['door_number', 'suburb', 'city', 'state', 'country'];
    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            element.value = '';
        }
    });
}

function displayError(message) {
    window.alert(message);
}

// Make sure initMap is globally available
window.initMap = initMap;

// Handle window resize
window.addEventListener('resize', function() {
    if (map) {
        google.maps.event.trigger(map, 'resize');
        const position = marker.getPosition();
        if (position) {
            map.setCenter(position);
        }
    }
});

// Add debugging code at the end
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    console.log('Google Maps API Key:', window.GOOGLE_MAPS_API_KEY);
    console.log('Map element:', document.getElementById('map'));
    console.log('Street address input:', document.getElementById('street_address'));
});

// Add this at the end
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error: ' + msg + '\nURL: ' + url + '\nLine: ' + lineNo + '\nColumn: ' + columnNo + '\nError object: ' + JSON.stringify(error));
    return false;
};