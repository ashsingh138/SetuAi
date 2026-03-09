import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;


export const processVoice = async (transcript, sessionId, language = 'Hindi', chatHistory = '') => {
  try {
    const response = await axios.post(`${API_BASE_URL}/process-voice`, {
      transcript,
      session_id: sessionId,
      language,
      chat_history: chatHistory 
    });
    return response.data;
  } catch (error) {
    console.error("Error processing voice:", error);
    throw error;
  }
};


export const locateCenter = async (lat, lng) => {
  try {
    
    const query = `
      [out:json];
      (
        node["amenity"="post_office"](around:5000,${lat},${lng});
        node["amenity"="townhall"](around:5000,${lat},${lng});
        node["amenity"="community_centre"](around:5000,${lat},${lng});
      );
      out tags center 1;
    `;
    
    const response = await axios.post('https://overpass-api.de/api/interpreter', query, {
      headers: { 'Content-Type': 'text/plain' }
    });

    if (response.data.elements && response.data.elements.length > 0) {
      const place = response.data.elements[0];
      const name = place.tags.name || place.tags.amenity.replace('_', ' ').toUpperCase();
      
      return {
        center_name: name,
        address: `Actual Location: Lat ${place.lat.toFixed(3)}, Lng ${place.lon.toFixed(3)}`,
        distance_km: "Nearby" 
      };
    }
    
   
    return { 
      center_name: "Nearest District Office", 
      address: `Coordinates: ${lat.toFixed(4)}, ${lng.toFixed(4)}`, 
      distance_km: "~2.5" 
    };
  } catch (error) {
    console.error("Map API Error:", error);
    return null;
  }
};