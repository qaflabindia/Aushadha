import { useState, useCallback, useRef, useEffect } from 'react';
import { useAlertContext } from '../context/Alert';

interface SpeechRecognitionHook {
  transcript: string;
  isListening: boolean;
  isTranscribing?: boolean;
  startListening: () => void;
  stopListening: () => void;
  resetTranscript: () => void;
  isSupported: boolean;
}

interface SpeechRecognitionOptions {
  language?: string; // BCP 47 language tag (e.g., 'hi-IN', 'ta-IN')
}

const BACKEND = import.meta.env.VITE_BACKEND_API_URL ?? '';

const useSpeechRecognition = (options?: SpeechRecognitionOptions): SpeechRecognitionHook => {
  const language = options?.language || 'en-US';
  const [transcript, setTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const { showAlert } = useAlertContext();

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const isNativeSupported =
    typeof window !== 'undefined' && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);
  const isMediaDevicesSupported =
    typeof window !== 'undefined' && Boolean(navigator.mediaDevices) && Boolean(window.MediaRecorder);
  const isSupported = isNativeSupported || isMediaDevicesSupported;

  useEffect(() => {
    if (!isNativeSupported) {
      return;
    }

    // Stop any previous instance before recreating
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {
        // Ignore errors during cleanup
      }
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
      showAlert('error', `Speech recognition error: ${event.error}`);
      setIsListening(false);
    };

    recognitionRef.current.onend = () => {
      setIsListening(false);
    };

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (_) {
          // Ignore errors during cleanup
        }
      }
    };
  }, [isNativeSupported, language]);

  const startListening = useCallback(async () => {
    if (!isSupported || isListening) {
      return;
    }
    setTranscript('');

    if (isNativeSupported) {
      recognitionRef.current?.start();
      setIsListening(true);
    } else if (isMediaDevicesSupported) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeTypes = ['audio/webm', 'audio/mp4', 'audio/ogg', 'audio/wav'];
        const supportedMimeType = mimeTypes.find((type) => MediaRecorder.isTypeSupported(type));

        const mediaRecorder = new MediaRecorder(
          stream,
          supportedMimeType ? { mimeType: supportedMimeType } : undefined
        );
        mediaRecorderRef.current = mediaRecorder;
        chunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            chunksRef.current.push(e.data);
          }
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(chunksRef.current, { type: supportedMimeType || 'audio/webm' });
          setIsTranscribing(true);
          try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');
            if (language) {
              // Extract the base language code (e.g., 'hi' from 'hi-IN')
              const langCode = language.split('-')[0];
              formData.append('language', langCode);
            }
            const response = await fetch(`${BACKEND}/audio/transcribe`, {
              method: 'POST',
              body: formData,
            });
            if (response.ok) {
              const data = await response.json();
              setTranscript(data.text);
            }
          } catch (error) {
            showAlert('error', 'Transcription fallback failed. Please try again.');
          } finally {
            setIsTranscribing(false);
            setIsListening(false);
          }
          // Stop all tracks to release microphone
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        setIsListening(true);
      } catch (err) {
        showAlert('error', 'Microphone access denied or failed.');
      }
    }
  }, [isSupported, isListening, isNativeSupported, isMediaDevicesSupported]);

  const stopListening = useCallback(() => {
    if (!isSupported || !isListening) {
      return;
    }

    if (isNativeSupported) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else if (isMediaDevicesSupported && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      // Note: setIsListening(false) will be called after transcription finishes in onstop
    }
  }, [isSupported, isListening, isNativeSupported, isMediaDevicesSupported]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
  }, []);

  return {
    transcript,
    isListening,
    isTranscribing,
    startListening,
    stopListening,
    resetTranscript,
    isSupported,
  };
};

export default useSpeechRecognition;
