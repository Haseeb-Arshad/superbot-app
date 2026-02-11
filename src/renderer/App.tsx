import React, { useState, useEffect } from 'react';
import { Mic, MessageSquare, Pin, Minus, X, Activity } from 'lucide-react';

const { ipcRenderer } = window.require('electron');

function App() {
    const [alwaysOnTop, setAlwaysOnTop] = useState(false);
    const [messages, setMessages] = useState<{ role: string, text: string }[]>([]);
    const [status, setStatus] = useState('Idle');

    const toggleAlwaysOnTop = () => {
        const newState = !alwaysOnTop;
        setAlwaysOnTop(newState);
        ipcRenderer.send('toggle-always-on-top', newState);
    };

    const testBackend = async () => {
        try {
            const res = await fetch('http://127.0.0.1:8000/test');
            const data = await res.json();
            setMessages(prev => [...prev, { role: 'bot', text: data.message }]);
        } catch (err) {
            console.error(err);
            setMessages(prev => [...prev, { role: 'system', text: 'Backend error' }]);
        }
    };

    return (
        <div className="flex flex-col h-screen w-full bg-gray-900 text-gray-100 border border-gray-700 rounded-lg overflow-hidden">
            {/* Title Bar / Drag Region */}
            <div className="h-10 bg-gray-800 flex items-center justify-between px-3 select-none" style={{ WebkitAppRegion: 'drag' } as any}>
                <div className="flex items-center space-x-2 text-sm font-semibold text-teal-400">
                    <Activity size={16} />
                    <span>Super-Bot</span>
                </div>
                <div className="flex items-center space-x-2 no-drag" style={{ WebkitAppRegion: 'no-drag' } as any}>
                    <button onClick={toggleAlwaysOnTop} className={`p-1 hover:bg-gray-700 rounded ${alwaysOnTop ? 'text-teal-400' : 'text-gray-400'}`}>
                        <Pin size={16} />
                    </button>
                    <button onClick={() => ipcRenderer.send('minimize-window')} className="p-1 hover:bg-gray-700 rounded text-gray-400">
                        <Minus size={16} />
                    </button>
                    <button onClick={() => ipcRenderer.send('close-window')} className="p-1 hover:bg-red-500 rounded text-gray-400 hover:text-white">
                        <X size={16} />
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col p-4 space-y-4 overflow-hidden">

                {/* Visualizer / Status Area */}
                <div className="h-32 bg-gray-800 rounded-lg flex items-center justify-center relative overflow-hidden group">
                    <div className={`absolute inset-0 bg-gradient-to-r from-teal-900/20 to-purple-900/20 opacity-50 transition-opacity duration-300 ${status === 'Listening' ? 'opacity-100' : ''}`} />

                    <div className="z-10 text-center">
                        <Mic size={48} className={`mx-auto mb-2 transition-colors duration-300 ${status === 'Listening' ? 'text-teal-400 animate-pulse' : 'text-gray-600'}`} />
                        <p className="text-sm font-mono text-gray-400">{status}</p>
                    </div>
                </div>

                {/* Chat History */}
                <div className="flex-1 bg-gray-800/50 rounded-lg p-3 overflow-y-auto space-y-2 custom-scrollbar">
                    {messages.length === 0 && (
                        <div className="text-center text-gray-600 mt-10">
                            <MessageSquare size={32} className="mx-auto mb-2 opacity-50" />
                            <p className="text-xs">No messages yet.</p>
                        </div>
                    )}
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${msg.role === 'user' ? 'bg-teal-600 text-white' :
                                    msg.role === 'bot' ? 'bg-gray-700 text-gray-200' : 'bg-red-900/50 text-red-200'
                                }`}>
                                {msg.text}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Controls */}
                <div className="flex space-x-2">
                    <button
                        onClick={() => {
                            setStatus('Listening');
                            setMessages(prev => [...prev, { role: 'user', text: 'Hello Python' }]);
                            testBackend();
                        }}
                        className="flex-1 bg-teal-600 hover:bg-teal-500 text-white py-2 rounded-lg text-sm font-medium transition-colors"
                    >
                        Test Connection
                    </button>
                </div>

            </div>
        </div>
    )
}

export default App
