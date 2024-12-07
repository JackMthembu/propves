let autocomplete;
let map;
let marker;

function initAutocomplete() {
    console.log('Initializing Google Maps Autocomplete...');
    
    const addressInput = document.getElementById('street_address');
    if (!addressInput) {
        console.error('Could not find street_address input element');
        return;
    }

    try {
        autocomplete = new google.maps.places.Autocomplete(addressInput, {
            types: ['address']
        });

        autocomplete.addListener('place_changed', fillInAddress);
        console.log('Autocomplete initialized successfully');

        initMap();
    } catch (error) {
        console.error('Error initializing autocomplete:', error);
        document.getElementById('map-error').textContent = 'Error initializing map functionality';
        document.getElementById('map-error').style.display = 'block';
    }
}

function fillInAddress() {
    try {
        const place = autocomplete.getPlace();
        console.log('Selected place:', place);

        if (!place.geometry) {
            window.alert("No details available for input: '" + place.name + "'");
            return;
        }

        const lat = place.geometry.location.lat();
        const lng = place.geometry.location.lng();

        document.getElementById('latitude').value = lat;
        document.getElementById('longitude').value = lng;

        // Clear existing values
        document.getElementById('suburb').value = '';
        document.getElementById('city').value = '';
        document.getElementById('state_id').value = '';
        document.getElementById('country_id').value = '';

        let stateComponent = null;
        let countryComponent = null;

        // First pass: find primary components
        for (const component of place.address_components) {
            if (component.types.includes('administrative_area_level_1')) {
                stateComponent = component;
            }
            if (component.types.includes('country')) {
                countryComponent = component;
            }
            if (component.types.includes('locality') || component.types.includes('postal_town')) {
                document.getElementById('city').value = component.long_name;
            }
            if (component.types.includes('sublocality_level_1') || 
                component.types.includes('neighborhood') || 
                component.types.includes('suburb')) {
                document.getElementById('suburb').value = component.long_name;
            }
        }

        // Set state and country if found
        if (stateComponent) {
            document.getElementById('state_id').value = stateComponent.short_name;
        }
        if (countryComponent) {
            document.getElementById('country_id').value = countryComponent.short_name;
        }

        // If suburb is still empty, try alternative fields
        if (!document.getElementById('suburb').value) {
            const suburbComponent = place.address_components.find(component => 
                component.types.includes('sublocality') ||
                component.types.includes('neighborhood') ||
                component.types.includes('district') ||
                component.types.includes('administrative_area_level_2')
            );
            if (suburbComponent) {
                document.getElementById('suburb').value = suburbComponent.long_name;
            }
        }

        // Log the final values for debugging
        console.log('Final values:', {
            street: document.getElementById('street_address').value,
            suburb: document.getElementById('suburb').value,
            city: document.getElementById('city').value,
            state: document.getElementById('state_id').value,
            country: document.getElementById('country_id').value,
            lat: lat,
            lng: lng
        });

        updateMap(lat, lng);
    } catch (error) {
        console.error('Error in fillInAddress:', error);
    }
}

function initMap() {
    document.getElementById('map-loading').style.display = 'none';
    document.getElementById('map').style.display = 'block';

    map = new google.maps.Map(document.getElementById('map'), {
        center: { lat: 0, lng: 0 }, // Center of the world
        zoom: 2, // Zoomed out to show the whole world
    });

    marker = new google.maps.Marker({
        map: map,
    });
}

function updateMap(lat, lng) {
    const location = { lat: lat, lng: lng };
    marker.setPosition(location);
    map.setCenter(location);
    map.setZoom(15);
}

// Add error handling for Google Maps loading
window.gm_authFailure = function() {
    console.error('Google Maps authentication failed');
    document.getElementById('map-error').textContent = 'Failed to load Google Maps';
    document.getElementById('map-error').style.display = 'block';
    document.getElementById('map-loading').style.display = 'none';
};
