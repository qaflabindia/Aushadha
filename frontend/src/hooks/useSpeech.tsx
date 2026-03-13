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
    if (!isSupported) {
      return;
    }
    setSpeaking(true);
    const utterance = new SpeechSynthesisUtterance();
    utterance.text = text;
    utterance.lang = lang;

    // Attempt to find a matching voice
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find((v) => v.lang === lang || v.lang.replace('_', '-') === lang);
    if (voice) {
      utterance.voice = voice;
    }

    utterance.onend = handleEnd;
    utterance.rate = rate;
    utterance.pitch = pitch;
    utterance.volume = volume;
    window.speechSynthesis.speak(utterance);
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
