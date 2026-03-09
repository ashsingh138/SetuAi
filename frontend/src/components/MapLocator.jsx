import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for React-Leaflet missing pin icons
const userIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34],
});
const centerIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34],
});

export default function MapLocator({ mapData }) {
  if (!mapData || !mapData.centers || mapData.centers.length === 0) return null;

  const { userLocation, centers } = mapData;

  return (
    <div className="w-full bg-white rounded-xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] border border-gray-100 overflow-hidden my-4">
      <div className="h-64 w-full relative z-0">
        <MapContainer center={[userLocation.lat, userLocation.lng]} zoom={13} className="h-full w-full">
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          
          <Marker position={[userLocation.lat, userLocation.lng]} icon={userIcon}>
            <Popup><span className="font-bold text-red-600">You are here</span></Popup>
          </Marker>

          {centers.map(center => (
            <Marker key={center.id} position={[center.lat, center.lng]} icon={centerIcon}>
              <Popup><strong>{center.name}</strong><br/>{center.distance} km away</Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="p-4 bg-gray-50">
        <h3 className="text-sm font-bold text-gray-800 mb-3">📍 Nearest Centers</h3>
        <ul className="space-y-3">
          {centers.map((center, index) => (
            <li key={center.id} className="flex justify-between items-center p-3 bg-white rounded-lg shadow-sm border border-gray-100">
              <div className="flex flex-col">
                <span className="font-semibold text-sm text-gray-800">{index + 1}. {center.name}</span>
                <span className="text-xs text-gray-500">{center.address}</span>
              </div>
              <span className="font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-md text-sm">{center.distance} km</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}