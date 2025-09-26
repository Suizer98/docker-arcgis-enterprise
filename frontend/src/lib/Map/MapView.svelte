<script lang="ts">
  import MapView from "@arcgis/core/views/MapView"
  import Expand from "@arcgis/core/widgets/Expand"
  import "@arcgis/core/assets/esri/themes/light/main.css"
  import { mapController } from './mapController'

  let view: MapView
  let expandWidget: Expand

  const createMap = (domNode: HTMLElement) => {
    view = new MapView({
      container: domNode,
      map: {
        basemap: "streets-vector",
      },
      zoom: 11,
      center: [103.8198, 1.3521],
      ui: {
        components: ["attribution"]
      }
    })

    // Register the map view with the controller
    mapController.setMapView(view)

    // Wait for view to be ready, then add widgets
    view.when(() => {
      // Create a simple text element with Esri widget style
      const resetText = document.createElement("div")
      resetText.textContent = "Reset View"
      resetText.style.cssText = `
        padding: 6px 8px;
        font-family: 'Avenir Next', 'Helvetica Neue', Arial, sans-serif;
        font-size: 12px;
        font-weight: 500;
        color: #323232;
        cursor: pointer;
        background: transparent;
        border: none;
        text-align: center;
        min-width: 70px;
        transition: color 0.2s ease;
      `
      
      // Add hover effect
      resetText.addEventListener('mouseenter', () => {
        resetText.style.color = '#0079c1'
      })
      
      resetText.addEventListener('mouseleave', () => {
        resetText.style.color = '#323232'
      })
      
      // Add click handler that resets rotation, tilt, and recenters
      resetText.addEventListener('click', () => {
        // Reset rotation and tilt
        view.rotation = 0
        view.tilt = 0
        
        // Recenter to default location and zoom
        view.goTo({
          center: [103.8198, 1.3521], // Default center (Singapore)
          zoom: 11 // Default zoom level
        })
        
        // Collapse the expand widget after action
        expandWidget.expanded = false
      })

      // Create Expand widget with Esri style text
      expandWidget = new Expand({
        view: view,
        content: resetText,
        expandIconClass: "esri-icon-locate",
        expandTooltip: "Reset View (Rotation & Tilt)",
        expanded: false,
        mode: "floating"
      })

      // Add the expand widget to the view
      view.ui.add(expandWidget, "top-left")
    })
  }
</script>

<div class="view" use:createMap></div>

<style>
  .view {
    height: 100vh;
    width: 100vw;
    position: relative;
  }
</style>
