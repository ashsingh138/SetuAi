import React from 'react';
import { MapPin } from 'lucide-react';

export default function MapLocator({ location }) {
  if (!location) return null;

  return (
    <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 shadow-sm mt-4 animate-fade-in">
      <div className="flex items-center gap-3 text-orange-800 mb-2">
        <MapPin size={24} />
        <h3 className="font-bold text-lg">नजदीकी सेवा केंद्र</h3>
      </div>
      <p className="font-semibold text-orange-900">{location.center_name}</p>
      <p className="text-sm text-orange-800 mb-1">{location.address}</p>
      <p className="text-xs font-bold text-orange-700 bg-orange-200 inline-block px-2 py-1 rounded mt-1">
        Distance: {location.distance_km} km
      </p>
    </div>
  );
}