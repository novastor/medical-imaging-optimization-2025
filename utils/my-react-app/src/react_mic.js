import React, { useState, useRef } from "react";
import { FaMicrophone, FaStop } from "react-icons/fa";
import "./styles.css"; // Your CSS file

export default function AudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Start recording using MediaRecorder with MIME type support for Firefox
  const startRecording = async () => {
    try {
      // Request audio stream
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Set up recording options. Firefox typically supports 'audio/ogg; codecs=opus'
      const mimeType =
        MediaRecorder.isTypeSupported("audio/ogg; codecs=opus")
          ? "audio/ogg; codecs=opus"
          : "audio/webm"; // Fallback to WebM if necessary
      
      const options = { mimeType };

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Listen for data as it becomes available
      mediaRecorder.addEventListener("dataavailable", event => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      });

      // When recording stops, combine the audio chunks and create a URL for playback
      mediaRecorder.addEventListener("stop", () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);
      });

      // Start the recording session
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Could not record audio:", error);
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="container">
      <header className="navbar">
        <h1>Audio Recorder (Firefox/Ubuntu Compatible)</h1>
      </header>
      <main className="content">
        <p>Click the button below to start or stop recording.</p>
        <div className="button-container">
          {isRecording ? (
            <button onClick={stopRecording} className="btn btn-stop">
              <FaStop /> Stop Recording
            </button>
          ) : (
            <button onClick={startRecording} className="btn btn-record">
              <FaMicrophone /> Start Recording
            </button>
          )}
        </div>

        {audioUrl && (
          <div className="audio-preview">
            <p>Recording complete. Listen to your audio:</p>
            <audio src={audioUrl} controls />
          </div>
        )}
      </main>
    </div>
  );
}
