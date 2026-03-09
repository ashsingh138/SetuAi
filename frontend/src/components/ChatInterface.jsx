import React from 'react';

export default function ChatInterface({ messages }) {
  return (
    <div className="flex flex-col space-y-4">
     {messages.map((msg, idx) => (
        <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} mb-4`}>
          <div className={`max-w-[85%] rounded-2xl p-4 shadow-sm text-lg ...`}>
            {msg.content}
          </div>
          
         
          {msg.eligibility && msg.eligibility !== "Pending Information" && (
            <div className={`mt-2 text-sm rounded-lg border overflow-hidden ${
              msg.eligibility.includes('Not') ? 'bg-red-50 border-red-200 text-red-800' : 
              msg.eligibility.includes('Almost') ? 'bg-yellow-50 border-yellow-200 text-yellow-800' : 
              'bg-green-50 border-green-200 text-green-800'
            }`}>
              
              
              <div className="px-4 py-2">
                <span className="font-bold">Status: {msg.eligibility}</span>
                {msg.eligibilityReason && <p className="text-xs mt-1 opacity-80">{msg.eligibilityReason}</p>}
              </div>

             
              {msg.eligibilityCriteria && msg.eligibilityCriteria.length > 0 && (
                <details className="border-t border-current/10 group">
                  <summary className="px-4 py-2 text-xs font-semibold cursor-pointer hover:bg-current/5 transition-colors focus:outline-none list-none flex justify-between items-center">
                    <span>View Eligibility Criteria</span>
                  
                    <span className="transition-transform group-open:rotate-180">▼</span>
                  </summary>
                  
                
                  <div className="px-4 pb-3 text-xs">
                    <ul className="space-y-2 mt-2">
                      {msg.eligibilityCriteria.map((item, i) => {
                       
                        const isObject = typeof item === 'object';
                        const criterionText = isObject ? item.criterion : item;
                        const status = isObject ? item.status : 'pending';

                        return (
                          <li key={i} className={`flex items-start gap-2 p-1.5 rounded-md ${
                            status === 'met' ? 'bg-green-100/50 text-green-800' : 
                            status === 'not_met' ? 'bg-red-100 border border-red-200 text-red-800 font-bold' : 
                            'bg-gray-100 text-gray-600'
                          }`}>
                            <span className="mt-0.5 text-sm">
                              {status === 'met' ? '✅' : 
                               status === 'not_met' ? '❌' : '⏳'}
                            </span>
                            <span className="leading-tight">{criterionText}</span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </details>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}