import React from 'react';
import { FileText } from 'lucide-react';

export default function PDFPreview({ url }) {
  if (!url) return null;

  return (
    <div className="bg-green-50 border border-green-200 rounded-xl p-4 shadow-sm mt-4 animate-fade-in">
      <div className="flex items-center gap-3 text-green-800 mb-2">
        <FileText size={24} />
        <h3 className="font-bold text-lg">आवेदन फॉर्म तैयार है</h3>
      </div>
      <p className="text-sm text-green-700 mb-3">Your application form has been generated successfully.</p>
      <a 
        href={url} 
        target="_blank" 
        rel="noreferrer" 
        className="block w-full text-center bg-green-600 text-white py-2 rounded-lg font-semibold hover:bg-green-700 transition-colors"
      >
        PDF डाउनलोड करें
      </a>
    </div>
  );
}