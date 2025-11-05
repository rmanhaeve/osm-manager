import { useEffect, useImperativeHandle, useRef, forwardRef } from 'react';
import L from 'leaflet';

export type MapPreviewHandle = {
  showBounds: (bounds: [[number, number], [number, number]]) => void;
};

const MapPreview = forwardRef<MapPreviewHandle>((_, ref) => {
  const mapRef = useRef<L.Map | null>(null);
  const boundsLayerRef = useRef<L.Rectangle | null>(null);

  useEffect(() => {
    const map = L.map('map-preview', {
      center: [43.7384, 7.4246],
      zoom: 12
    });

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      boundsLayerRef.current = null;
    };
  }, []);

  useImperativeHandle(
    ref,
    () => ({
      showBounds: (bounds: [[number, number], [number, number]]) => {
        if (mapRef.current) {
          if (boundsLayerRef.current) {
            boundsLayerRef.current.remove();
          }
          boundsLayerRef.current = L.rectangle(bounds, {
            color: '#2563eb',
            weight: 2,
            fillOpacity: 0.1
          }).addTo(mapRef.current);
          mapRef.current.fitBounds(bounds, { padding: [16, 16] });
        }
      }
    }),
    []
  );

  return <div id="map-preview" style={{ height: '320px', borderRadius: '0.75rem', overflow: 'hidden' }} />;
});

export default MapPreview;
