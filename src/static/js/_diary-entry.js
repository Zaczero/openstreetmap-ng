import * as L from "leaflet"
import { isLatitude, isLongitude, zoomPrecision } from "./_utils.js"
import { Mapnik } from "./leaflet/_osm.js"
import { getMarkerIcon } from "./leaflet/_utils.js"
import { getZoomControl } from "./leaflet/_zoom.js"

const useMapContainer = document.querySelector(".diary-entry-use-map-container")
if (useMapContainer) {
    const lonInput = useMapContainer.querySelector('input[name="longitude"]')
    const latInput = useMapContainer.querySelector('input[name="latitude"]')
    const useMapBtn = useMapContainer.querySelector(".diary-entry-use-map-btn")
    const mapDiv = useMapContainer.querySelector(".leaflet-container")

    // Null values until the map/marker is initialized
    let map = null
    let marker = null

    const markerFactory = (latlng) =>
        L.marker(latlng, { icon: getMarkerIcon() }).addTo(map).bindPopup(I18n.t("diary_entries.edit.marker_text"))

    // On map click, update the coordinates and move the marker
    const onMapClick = (e) => {
        const precision = zoomPrecision(map.getZoom())
        const lon = e.latlng.lng.toFixed(precision)
        const lat = e.latlng.lat.toFixed(precision)
        const latLng = L.latLng(lat, lon)

        lonInput.value = lon
        latInput.value = lat

        // If there's already a marker, move it, otherwise create a new one
        if (marker) marker.setLatLng(latLng)
        else marker = markerFactory(latLng)
    }

    // On "Use Map" button click, show the map and hide the button
    useMapBtn.addEventListener("click", () => {
        useMapBtn.classList.add("d-none")
        mapDiv.classList.remove("d-none")
        const params = mapDiv.dataset

        map = L.map(mapDiv, {
            attributionControl: false,
            zoomControl: false,
        }).addLayer(new Mapnik())

        // Add zoom control
        getZoomControl().addTo(map)

        let center

        // Attempt to parse the lat/lon from the inputs
        // If they're valid, use them as the initial center and display a marker
        if (lonInput.value && latInput.value) {
            const lon = parseFloat(lonInput.value)
            const lat = parseFloat(latInput.value)
            if (isLongitude(lon) && isLatitude(lat)) {
                center = L.latLng(lat, lon)
                marker = markerFactory(center)
            }
        }

        // When input is not valid, use the default center
        // This will only focus the map, not display a marker
        if (center === undefined) {
            center = L.latLng(params.lat, params.lon)
        }

        map.setView(center, params.zoom)
        map.addEventListener("click", onMapClick)
    })
}
