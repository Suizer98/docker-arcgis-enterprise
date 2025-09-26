// Map Controller for AI integration
import MapView from '@arcgis/core/views/MapView';
import GraphicsLayer from '@arcgis/core/layers/GraphicsLayer';
import Graphic from '@arcgis/core/Graphic';
import Polyline from '@arcgis/core/geometry/Polyline';
import Polygon from '@arcgis/core/geometry/Polygon';
import Point from '@arcgis/core/geometry/Point';
import Circle from '@arcgis/core/geometry/Circle';
import SimpleLineSymbol from '@arcgis/core/symbols/SimpleLineSymbol';
import SimpleFillSymbol from '@arcgis/core/symbols/SimpleFillSymbol';
import SimpleMarkerSymbol from '@arcgis/core/symbols/SimpleMarkerSymbol';

class MapController {
  private view: MapView | null = null;
  private listeners: Array<
    (center: { lat: number; lng: number }, zoom: number) => void
  > = [];
  private graphicsLayer: GraphicsLayer | null = null;
  private graphicMetadata: Map<string, { type: string; color: string }> =
    new Map();

  setMapView(view: MapView) {
    this.view = view;

    // Create graphics layer for drawing
    this.graphicsLayer = new GraphicsLayer();
    if (view.map) {
      view.map.add(this.graphicsLayer);
    }

    // Watch for changes and notify listeners
    view.watch('center', center => {
      if (center) {
        this.notifyListeners(
          {
            lat: center.latitude,
            lng: center.longitude,
          },
          view.zoom ?? 1
        );
      }
    });

    view.watch('zoom', zoom => {
      if (view.center) {
        this.notifyListeners(
          {
            lat: view.center.latitude ?? 0,
            lng: view.center.longitude ?? 0,
          },
          zoom ?? 1
        );
      }
    });
  }

  // Helper method to convert hex color to RGB
  private hexToRgb(hex: string): { r: number; g: number; b: number } {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : { r: 255, g: 0, b: 0 }; // Default to red
  }

  // Draw a line on the map
  async drawLine(
    startLat: number,
    startLng: number,
    endLat: number,
    endLng: number,
    color: string = '#FF0000'
  ): Promise<{ success: boolean; message: string }> {
    if (!this.view || !this.graphicsLayer) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      const polyline = new Polyline({
        paths: [
          [
            [startLng, startLat],
            [endLng, endLat],
          ],
        ], // ArcGIS uses [lng, lat] format
      });

      const rgb = this.hexToRgb(color);
      const lineSymbol = new SimpleLineSymbol({
        color: [rgb.r, rgb.g, rgb.b, 255],
        width: 3,
      });

      const graphic = new Graphic({
        geometry: polyline,
        symbol: lineSymbol,
      });

      this.graphicsLayer.add(graphic);

      // Store metadata for selective clearing
      const graphicId = `line_${Date.now()}_${Math.random()}`;
      this.graphicMetadata.set(graphicId, { type: 'lines', color: color });
      (graphic as any).customId = graphicId;

      return {
        success: true,
        message: `Line drawn from (${startLat.toFixed(4)}, ${startLng.toFixed(4)}) to (${endLat.toFixed(4)}, ${endLng.toFixed(4)})`,
      };
    } catch (error) {
      console.error('Error drawing line:', error);
      return {
        success: false,
        message: 'Failed to draw line',
      };
    }
  }

  // Draw a point on the map
  async drawPoint(
    lat: number,
    lng: number,
    color: string = '#FF0000',
    size: number = 10,
    label?: string,
    markerType: string = 'points',
    fillColor?: string | null,
    outlineColor?: string,
    outlineWidth?: number,
    opacity?: number,
    filled?: boolean
  ): Promise<{ success: boolean; message: string }> {
    if (!this.view || !this.graphicsLayer) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      const point = new Point({
        longitude: lng,
        latitude: lat,
      });

      const rgb = this.hexToRgb(color);
      const outlineRgb = this.hexToRgb(outlineColor || '#000000');
      const fillRgb = fillColor ? this.hexToRgb(fillColor) : rgb;
      const alpha = Math.round((opacity || 1) * 255);

      const markerSymbol = new SimpleMarkerSymbol({
        color: filled ? [fillRgb.r, fillRgb.g, fillRgb.b, alpha] : [0, 0, 0, 0], // Transparent if not filled
        size: size,
        outline: {
          color: [outlineRgb.r, outlineRgb.g, outlineRgb.b, 255],
          width: outlineWidth || 1,
        },
      });

      const graphic = new Graphic({
        geometry: point,
        symbol: markerSymbol,
      });

      this.graphicsLayer.add(graphic);

      // Store metadata for selective clearing
      const graphicId = `point_${Date.now()}_${Math.random()}`;
      this.graphicMetadata.set(graphicId, { type: markerType, color: color });
      (graphic as any).customId = graphicId;

      return {
        success: true,
        message: `Point drawn at (${lat.toFixed(4)}, ${lng.toFixed(4)})${label ? ` with label "${label}"` : ''}`,
      };
    } catch (error) {
      console.error('Error drawing point:', error);
      return {
        success: false,
        message: 'Failed to draw point',
      };
    }
  }

  // Draw circle on the map
  async drawCircle(options: {
    center: [number, number]; // [longitude, latitude]
    radius: number; // in meters
    color?: string;
    fillColor?: string | null;
    opacity?: number;
    filled?: boolean;
  }): Promise<{ success: boolean; message: string }> {
    if (!this.view || !this.graphicsLayer) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      const [lng, lat] = options.center;
      const radius = options.radius;
      const color = options.color || '#FF0000';
      const fillColor = options.filled ? options.fillColor || color : null;
      const opacity = options.opacity || 0.3;

      // Create circle as polygon by calculating points around the circumference
      const points = [];
      const numPoints = 64; // Number of points to create smooth circle

      for (let i = 0; i < numPoints; i++) {
        const angle = (i / numPoints) * 2 * Math.PI;
        const x =
          lng +
          ((radius / 111000) * Math.cos(angle)) /
            Math.cos((lat * Math.PI) / 180);
        const y = lat + (radius / 111000) * Math.sin(angle);
        points.push([x, y]);
      }

      // Close the polygon by adding the first point at the end
      points.push(points[0]);

      // Create polygon from circle points
      const polygon = new Polygon({
        rings: [points],
      });

      const rgb = this.hexToRgb(color);

      let fillSymbol;
      if (fillColor) {
        const fillRgb = this.hexToRgb(fillColor);
        fillSymbol = new SimpleFillSymbol({
          color: [fillRgb.r, fillRgb.g, fillRgb.b, Math.round(opacity * 255)],
          outline: {
            color: [rgb.r, rgb.g, rgb.b, 255],
            width: 2,
          },
        });
      } else {
        // No fill, just outline
        fillSymbol = new SimpleFillSymbol({
          color: [0, 0, 0, 0], // Transparent fill
          outline: {
            color: [rgb.r, rgb.g, rgb.b, 255],
            width: 2,
          },
        });
      }

      const graphic = new Graphic({
        geometry: polygon,
        symbol: fillSymbol,
      });

      this.graphicsLayer.add(graphic);

      // Store metadata for selective clearing
      const graphicId = `circle_${Date.now()}_${Math.random()}`;
      this.graphicMetadata.set(graphicId, { type: 'circles', color: color });
      (graphic as any).customId = graphicId;

      return {
        success: true,
        message: `Circle drawn at (${lat.toFixed(4)}, ${lng.toFixed(4)}) with radius ${(radius / 1000).toFixed(2)}km`,
      };
    } catch (error) {
      console.error('Error drawing circle:', error);
      return {
        success: false,
        message: 'Failed to draw circle',
      };
    }
  }

  // Draw rectangle on the map
  async drawRectangle(options: {
    southwest: [number, number]; // [longitude, latitude]
    northeast: [number, number]; // [longitude, latitude]
    color?: string;
    fillColor?: string;
    opacity?: number;
  }): Promise<{ success: boolean; message: string }> {
    if (!this.view || !this.graphicsLayer) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      const [swLng, swLat] = options.southwest;
      const [neLng, neLat] = options.northeast;
      const color = options.color || '#FF0000';
      const fillColor = options.fillColor || color;
      const opacity = options.opacity || 0.3;

      // Create rectangle polygon
      const rectangle = new Polygon({
        rings: [
          [
            [swLng, swLat], // Southwest
            [neLng, swLat], // Southeast
            [neLng, neLat], // Northeast
            [swLng, neLat], // Northwest
            [swLng, swLat], // Close the ring
          ],
        ],
      });

      const rgb = this.hexToRgb(color);
      const fillRgb = this.hexToRgb(fillColor);

      const fillSymbol = new SimpleFillSymbol({
        color: [fillRgb.r, fillRgb.g, fillRgb.b, Math.round(opacity * 255)],
        outline: {
          color: [rgb.r, rgb.g, rgb.b, 255],
          width: 2,
        },
      });

      const graphic = new Graphic({
        geometry: rectangle,
        symbol: fillSymbol,
      });

      this.graphicsLayer.add(graphic);

      // Store metadata for selective clearing
      const graphicId = `rectangle_${Date.now()}_${Math.random()}`;
      this.graphicMetadata.set(graphicId, { type: 'rectangles', color: color });
      (graphic as any).customId = graphicId;

      return {
        success: true,
        message: `Rectangle drawn from (${swLat.toFixed(4)}, ${swLng.toFixed(4)}) to (${neLat.toFixed(4)}, ${neLng.toFixed(4)})`,
      };
    } catch (error) {
      console.error('Error drawing rectangle:', error);
      return {
        success: false,
        message: 'Failed to draw rectangle',
      };
    }
  }

  // Draw polygon on the map
  async drawPolygon(options: {
    vertices: [number, number][]; // Array of [longitude, latitude] pairs
    color?: string;
    fillColor?: string;
    opacity?: number;
  }): Promise<{ success: boolean; message: string }> {
    if (!this.view || !this.graphicsLayer) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      const vertices = options.vertices;
      const color = options.color || '#FF0000';
      const fillColor = options.fillColor || color;
      const opacity = options.opacity || 0.3;

      if (vertices.length < 3) {
        return {
          success: false,
          message: 'Polygon must have at least 3 vertices',
        };
      }

      // Close the polygon by adding the first vertex at the end
      const closedVertices = [...vertices, vertices[0]];

      // Create polygon
      const polygon = new Polygon({
        rings: [closedVertices],
      });

      const rgb = this.hexToRgb(color);
      const fillRgb = this.hexToRgb(fillColor);

      const fillSymbol = new SimpleFillSymbol({
        color: [fillRgb.r, fillRgb.g, fillRgb.b, Math.round(opacity * 255)],
        outline: {
          color: [rgb.r, rgb.g, rgb.b, 255],
          width: 2,
        },
      });

      const graphic = new Graphic({
        geometry: polygon,
        symbol: fillSymbol,
      });

      this.graphicsLayer.add(graphic);

      // Store metadata for selective clearing
      const graphicId = `polygon_${Date.now()}_${Math.random()}`;
      this.graphicMetadata.set(graphicId, { type: 'polygons', color: color });
      (graphic as any).customId = graphicId;

      return {
        success: true,
        message: `Polygon drawn with ${vertices.length} vertices`,
      };
    } catch (error) {
      console.error('Error drawing polygon:', error);
      return {
        success: false,
        message: 'Failed to draw polygon',
      };
    }
  }

  // Clear graphics from the map
  async clearGraphics(
    type: string = 'all',
    color?: string
  ): Promise<{ success: boolean; message: string }> {
    if (!this.graphicsLayer) {
      return { success: false, message: 'Graphics layer not initialized' };
    }

    try {
      if (type === 'all' && !color) {
        // Clear all graphics
        this.graphicsLayer.removeAll();
        this.graphicMetadata.clear();
        return { success: true, message: 'All graphics cleared' };
      } else {
        // Clear specific graphics
        const graphicsToRemove: Graphic[] = [];

        this.graphicsLayer.graphics.forEach(graphic => {
          const graphicId = (graphic as any).customId;
          const metadata = graphicId
            ? this.graphicMetadata.get(graphicId)
            : null;

          if (metadata) {
            let shouldRemove = false;

            // Check type filter
            if (
              type === 'all' ||
              metadata.type === type ||
              (type === 'markers' && metadata.type === 'location')
            ) {
              shouldRemove = true;
            }

            // Check color filter
            if (color && metadata.color !== color) {
              shouldRemove = false;
            }

            if (shouldRemove) {
              graphicsToRemove.push(graphic);
            }
          }
        });

        // Remove selected graphics
        graphicsToRemove.forEach(graphic => {
          this.graphicsLayer!.remove(graphic);
          const graphicId = (graphic as any).customId;
          if (graphicId) {
            this.graphicMetadata.delete(graphicId);
          }
        });

        let message = `${type} graphics cleared`;
        if (color) {
          message += ` (${color} color only)`;
        }

        return { success: true, message };
      }
    } catch (error) {
      console.error('Error clearing graphics:', error);
      return { success: false, message: 'Failed to clear graphics' };
    }
  }

  // Set map center
  async setCenter(
    latitude: number,
    longitude: number
  ): Promise<{ success: boolean; message: string }> {
    if (!this.view) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      await this.view.goTo({
        center: [longitude, latitude], // ArcGIS uses [lng, lat] format
        animate: true,
      });

      return {
        success: true,
        message: `Map center set to ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
      };
    } catch (error) {
      console.error('Error setting map center:', error);
      return {
        success: false,
        message: 'Failed to set map center',
      };
    }
  }

  // Set zoom level
  async setZoom(level: number): Promise<{ success: boolean; message: string }> {
    if (!this.view) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      await this.view.goTo({
        zoom: level,
        animate: true,
      });

      return {
        success: true,
        message: `Map zoom set to level ${level}`,
      };
    } catch (error) {
      console.error('Error setting zoom:', error);
      return {
        success: false,
        message: 'Failed to set zoom level',
      };
    }
  }

  // Set both center and zoom
  async setCenterAndZoom(
    latitude: number,
    longitude: number,
    zoom: number
  ): Promise<{ success: boolean; message: string }> {
    if (!this.view) {
      return { success: false, message: 'Map not initialized' };
    }

    try {
      await this.view.goTo({
        center: [longitude, latitude],
        zoom: zoom,
        animate: true,
      });

      return {
        success: true,
        message: `Map set to ${latitude.toFixed(4)}, ${longitude.toFixed(4)} at zoom level ${zoom}`,
      };
    } catch (error) {
      console.error('Error setting map view:', error);
      return {
        success: false,
        message: 'Failed to set map view',
      };
    }
  }

  // Get current map state
  getCurrentState(): {
    center: { lat: number; lng: number };
    zoom: number;
  } | null {
    if (!this.view || !this.view.center) {
      return null;
    }

    return {
      center: {
        lat: this.view.center.latitude ?? 0,
        lng: this.view.center.longitude ?? 0,
      },
      zoom: this.view.zoom ?? 1,
    };
  }

  // Get user's current location using geolocation
  async getCurrentLocation(): Promise<{
    success: boolean;
    message: string;
    coordinates?: { lat: number; lng: number };
    accuracy?: number;
  }> {
    if (!navigator.geolocation) {
      return {
        success: false,
        message: 'Geolocation is not supported by this browser',
      };
    }

    return new Promise(resolve => {
      navigator.geolocation.getCurrentPosition(
        position => {
          const coordinates = {
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          };

          resolve({
            success: true,
            message: `Current location found: ${coordinates.lat.toFixed(6)}, ${coordinates.lng.toFixed(6)}`,
            coordinates,
            accuracy: position.coords.accuracy,
          });
        },
        error => {
          let message = 'Unable to retrieve your location';

          switch (error.code) {
            case error.PERMISSION_DENIED:
              message =
                'Location access denied by user. Please enable location permissions.';
              break;
            case error.POSITION_UNAVAILABLE:
              message = 'Location information is unavailable.';
              break;
            case error.TIMEOUT:
              message = 'Location request timed out.';
              break;
          }

          resolve({
            success: false,
            message,
          });
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000, // 5 minutes
        }
      );
    });
  }

  // Center map on user's current location
  async centerOnCurrentLocation(): Promise<{
    success: boolean;
    message: string;
    coordinates?: { lat: number; lng: number };
  }> {
    const locationResult = await this.getCurrentLocation();

    if (!locationResult.success || !locationResult.coordinates) {
      return {
        success: false,
        message: locationResult.message,
      };
    }

    const { lat, lng } = locationResult.coordinates;
    const centerResult = await this.setCenter(lat, lng);

    if (centerResult.success) {
      return {
        success: true,
        message: `Map centered on your current location: ${lat.toFixed(6)}, ${lng.toFixed(6)}`,
        coordinates: { lat, lng },
      };
    } else {
      return {
        success: false,
        message: `Found your location but failed to center map: ${centerResult.message}`,
      };
    }
  }

  // Add listener for map changes
  addListener(
    callback: (center: { lat: number; lng: number }, zoom: number) => void
  ) {
    this.listeners.push(callback);
  }

  // Remove listener
  removeListener(
    callback: (center: { lat: number; lng: number }, zoom: number) => void
  ) {
    this.listeners = this.listeners.filter(listener => listener !== callback);
  }

  // Notify all listeners
  private notifyListeners(center: { lat: number; lng: number }, zoom: number) {
    this.listeners.forEach(listener => listener(center, zoom));
  }
}

// Export singleton instance
export const mapController = new MapController();
