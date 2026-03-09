import React, { useState, useEffect, useRef } from 'react';
import ChatInterface from './components/ChatInterface';
import ChatInput from './components/ChatInput';
import PDFPreview from './components/PDFPreview';
import MapLocator from './components/MapLocator';
import { processVoice, locateCenter } from './services/api';
import { generateRealPdf } from './utils/pdfGenerator';

const SUPPORTED_LANGUAGES = {
  'Hindi': { code: 'hi-IN', label: 'हिन्दी', greeting: 'नमस्ते! मैं सेतु हूँ। मैं सरकारी योजनाओं में आपकी मदद कर सकता हूँ। आप क्या सहायता चाहते हैं?' },
  'English': { code: 'en-IN', label: 'English', greeting: 'Hello! I am Setu. I can help you with government schemes. How can I assist you?' },
  'Tamil': { code: 'ta-IN', label: 'தமிழ்', greeting: 'வணக்கம்! நான் சேது. அரசு திட்டங்களில் நான் உங்களுக்கு உதவ முடியும். நான் உங்களுக்கு எப்படி உதவ முடியும்?' },
  'Bengali': { code: 'bn-IN', label: 'বাংলা', greeting: 'নমস্কার! আমি সেতু। আমি আপনাকে সরকারি প্রকল্পে সাহায্য করতে পারি। আপনি কী ধরনের সহায়তা চান?' },
  'Marathi': { code: 'mr-IN', label: 'मराठी', greeting: 'नमस्कार! मी सेतू आहे. मी तुम्हाला सरकारी योजनांमध्ये मदत करू शकतो. मी तुमची कशी मदत करू शकतो?' },
  'Telugu': { code: 'te-IN', label: 'తెలుగు', greeting: 'నమస్కారం! నేను సేతును. ప్రభుత్వ పథకాలలో నేను మీకు సహాయం చేయగలను. నేను మీకు ఎలా సహాయపడగలను?' }
};

export default function App() {
  const [language, setLanguage] = useState('Hindi');
  const [messages, setMessages] = useState([
    { role: 'system', content: SUPPORTED_LANGUAGES['Hindi'].greeting }
  ]);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [pdfUrl, setPdfUrl] = useState(null);
  const [cscLocation, setCscLocation] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  
  const handleLanguageChange = (e) => {
    const newLang = e.target.value;
    setLanguage(newLang);
   
    setMessages([{ role: 'system', content: SUPPORTED_LANGUAGES[newLang].greeting }]);
    setPdfUrl(null);
    setCscLocation(null);
  };

  const speakText = (text) => {
    const synth = window.speechSynthesis;
    
    synth.cancel(); 
    const utterance = new SpeechSynthesisUtterance(text);
    
    utterance.lang = SUPPORTED_LANGUAGES[language].code;
    synth.speak(utterance);
  };

 const handleVoiceTranscript = async (transcript) => {
   
    setPdfUrl(null);
    setCscLocation(null);

   
    const newMessages = [...messages, { role: 'user', content: transcript }];
    setMessages(newMessages);
    setIsProcessing(true);
    
    try {
      const chatHistoryString = newMessages.slice(-6).map(m => `${m.role === 'user' ? 'User' : 'Setu AI'}: ${m.content}`).join('\n');
      const aiResponse = await processVoice(transcript, sessionId, language, chatHistoryString);
      
      const replyText = aiResponse.response_text || "Processing...";
      
     
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: replyText,
        eligibility: aiResponse.eligibility_status,
        eligibilityReason: aiResponse.eligibility_reason,
        eligibilityCriteria: aiResponse.eligibility_criteria || []
      }]);
      speakText(replyText);

     
      const hasNoMissingFields = !aiResponse.missing_fields || aiResponse.missing_fields.length === 0;
      
      const isEligible = aiResponse.eligibility_status === 'Eligible' || aiResponse.eligibility_status === 'Almost Eligible';

      
      if (aiResponse.intent === 'apply_scheme' && hasNoMissingFields && isEligible) {
        await handleApplicationReady(aiResponse.entities, 'apply_scheme', null);
      } 
      
      else if (aiResponse.intent === 'file_rti' && hasNoMissingFields) {
        await handleApplicationReady(aiResponse.entities, 'file_rti', aiResponse.rti_draft_text);
      }
      
      
    } catch (error) {
      const errorMsg = language === 'English' ? 'Sorry, server error.' : 'क्षमा करें, सर्वर से संपर्क नहीं हो पा रहा है।';
      setMessages(prev => [...prev, { role: 'system', content: errorMsg }]);
      speakText(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplicationReady = async (userData, intentType, rtiText) => {
    const generatingMsg = language === 'English' ? 'Preparing your document...' : 'मैं आपका दस्तावेज़ तैयार कर रहा हूँ...';
    setMessages(prev => [...prev, { role: 'system', content: generatingMsg }]);
    
    
    let finalPdfUrl;
    if (intentType === 'file_rti') {
        finalPdfUrl = generateRtiPdf(userData, rtiText);
    } else {
        finalPdfUrl = generateRealPdf(userData);
    }
    
    setPdfUrl(finalPdfUrl);

    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          
          const locationResult = await locateCenter(lat, lng);
          setCscLocation(locationResult);
          
          const successMsg = language === 'English' ? "Your form is ready and nearby center located." : "आपका फॉर्म तैयार है और मैंने नजदीकी केंद्र खोज लिया है।";
          speakText(successMsg);
        },
        (error) => {
          console.warn("Location denied by user.");
          setCscLocation({ center_name: "Location Access Denied", address: "Please enable GPS", distance_km: "N/A" });
          const noGpsMsg = language === 'English' ? "Form ready, but location not found." : "आपका फॉर्म तैयार है, लेकिन लोकेशन नहीं मिल पाई।";
          speakText(noGpsMsg);
        }
      );
    } else {
      speakText(language === 'English' ? "Your form is ready." : "आपका फॉर्म तैयार है।");
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-md mx-auto bg-white shadow-xl relative overflow-hidden">
      <header className="bg-blue-600 text-white p-4 shadow-md z-10 flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <span className="text-3xl">🌉</span> Setu AI
        </h1>
        
       
        <select 
          value={language} 
          onChange={handleLanguageChange}
          className="bg-blue-700 text-white text-sm font-medium px-3 py-1.5 rounded-lg border border-blue-400 outline-none focus:ring-2 focus:ring-white cursor-pointer"
        >
          {Object.entries(SUPPORTED_LANGUAGES).map(([key, data]) => (
            <option key={key} value={key}>{data.label}</option>
          ))}
        </select>
      </header>

      <main className="flex-1 overflow-y-auto p-4 space-y-4 pb-32 bg-slate-50">
        <ChatInterface messages={messages} />
        <PDFPreview url={pdfUrl} />
        <MapLocator location={cscLocation} />
      </main>

     
      <ChatInput onInput={handleVoiceTranscript} disabled={isProcessing} languageCode={SUPPORTED_LANGUAGES[language].code} />
    </div>
  );
}