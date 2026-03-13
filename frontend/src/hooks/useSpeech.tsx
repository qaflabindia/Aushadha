import { useState } from 'react';
import { SpeechSynthesisProps, SpeechArgs } from '../types';

const useSpeechSynthesis = (props: SpeechSynthesisProps = {}) => {
  const { onEnd = () => {} } = props;
  const [speaking, setSpeaking] = useState(false);
  const handleEnd = () => {
    setSpeaking(false);
    onEnd();
  };

  const speak = (args: SpeechArgs = {}, isSupported: boolean) => {
    const { text = '', rate = 1, pitch = 1, volume = 1, lang = 'en-US' } = args;
    if (!isSupported || typeof window === 'undefined') {
      return;
    }

    const startSpeaking = () => {
      setSpeaking(true);
      const utterance = new SpeechSynthesisUtterance();
      utterance.text = text;
      utterance.lang = lang;

      const voices = window.speechSynthesis.getVoices();
      // Try to find a voice that matches the lang exactly or partially
      const voice = voices.find(
        (v) => v.lang === lang || v.lang.replace('_', '-') === lang || v.lang.startsWith(lang.split('-')[0])
      );
      if (voice) {
        utterance.voice = voice;
      }

      utterance.onend = handleEnd;
      utterance.rate = rate;
      utterance.pitch = pitch;
      utterance.volume = volume;
      window.speechSynthesis.speak(utterance);
    };

    if (window.speechSynthesis.getVoices().length === 0) {
      window.speechSynthesis.onvoiceschanged = () => {
        startSpeaking();
        window.speechSynthesis.onvoiceschanged = null;
      };
    } else {
      startSpeaking();
    }
  };
  const cancel = () => {
    setSpeaking(false);
    window.speechSynthesis.cancel();
  };
  return {
    speak,
    speaking,
    cancel,
  };
};
export default useSpeechSynthesis;
