import { useState, useCallback, useRef, useEffect } from 'react';

interface SpeechRecognitionHook {
  transcript: string;
  isListening: boolean;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  isSupported: boolean;
}

interface SpeechRecognitionOptions {
  language?: string; // BCP 47 language tag (e.g., 'hi-IN', 'ta-IN')
}

const useSpeechRecognition = (options?: SpeechRecognitionOptions): SpeechRecognitionHook => {
  const language = options?.language || 'en-US';
  const [transcript, setTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const isSupported = typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);

  useEffect(() => {
    if (!isSupported) return;

    // Stop any previous instance before recreating
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = language;

    recognitionRef.current.onresult = (event: any) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }
      
      if (finalTranscript || interimTranscript) {
        setTranscript(finalTranscript || interimTranscript);
      }
    };

    recognitionRef.current.onerror = (event: any) => {
      console.error('Speech recognition error', event.error);
      setIsListening(false);
    };

    recognitionRef.current.onend = () => {
      setIsListening(false);
    };

    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (_) {}
      }
    };
  }, [isSupported, language]);

  const startListening = useCallback(() => {
    if (!isSupported || isListening) return;
    setTranscript('');
    recognitionRef.current?.start();
    setIsListening(true);
  }, [isSupported, isListening]);

  const stopListening = useCallback(() => {
    if (!isSupported || !isListening) return;
    recognitionRef.current?.stop();
    setIsListening(false);
  }, [isSupported, isListening]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  return {
    transcript,
    isListening,
    startListening,
    stopListening,
    resetTranscript,
    isSupported,
  };
};

export default useSpeechRecognition;
