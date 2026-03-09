import React, { useState, useEffect, useRef } from 'react';
import { Mic, Square, Send } from 'lucide-react';


export default function ChatInput({ onInput, disabled, languageCode }) {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      
      
      recognition.lang = languageCode || 'en-IN'; 
      
      recognition.interimResults = false;

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        onInput(transcript);
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
 
  }, [onInput, languageCode]);

  const toggleRecording = () => {
    if (disabled) return;
    if (isRecording) {
      recognitionRef.current?.stop();
    } else {
      recognitionRef.current?.start();
      setIsRecording(true);
    }
  };

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onInput(text);
      setText('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleSend();
  };

  return (
    <footer className="absolute bottom-4 left-4 right-4 bg-white/90 backdrop-blur-lg border border-gray-200/50 p-2 rounded-2xl flex items-center gap-2 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
      <button
        onClick={toggleRecording}
        disabled={disabled}
        className={`flex-shrink-0 relative flex items-center justify-center w-12 h-12 rounded-full text-white transition-all duration-300 ${
          isRecording ? 'bg-red-500 animate-pulse' : disabled ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        {isRecording ? <Square size={20} /> : <Mic size={24} />}
        {isRecording && <span className="absolute w-full h-full rounded-full border-2 border-red-500 animate-ping opacity-75"></span>}
      </button>
      
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled || isRecording}
        placeholder={isRecording ? 'Listening...' : 'Type your message...'}
        className="flex-1 bg-gray-100 rounded-full px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      />
      
      <button
        onClick={handleSend}
        disabled={!text.trim() || disabled || isRecording}
        className="flex-shrink-0 w-12 h-12 flex items-center justify-center rounded-full bg-green-500 text-white hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
      >
        <Send size={20} className="ml-1" />
      </button>
    </footer>
  );
}