import { useEffect } from 'react';
import L from 'leaflet';

const MapPreview = () => {
  useEffect(() => {
    const map = L.map('map-preview', {
      center: [43.7384, 7.4246],
      zoom: 12
    });

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    return () => {
      map.remove();
    };
  }, []);

  return <div id="map-preview" style={{ height: '320px', borderRadius: '0.75rem', overflow: 'hidden' }} />;
};

export default MapPreview;
