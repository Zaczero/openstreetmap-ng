import "./_tracking.js"

import "./_bootstrap.js"
import "./_i18n.js"

import "./_fixthemap.js"
import "./_id-iframe.js"
import "./_rapid-iframe.js"
import "./_welcome.js"
import { configureMainMap } from "./leaflet/_main-map.js"
import "./user/_account-confirm.js"
import "./user/_login.js"
import "./user/_settings.js"
import "./user/_signup.js"
import "./user/_terms.js"

const mapContainer = document.querySelector(".main-map")
if (mapContainer) configureMainMap(mapContainer)
