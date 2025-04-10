//some code snippets developed from gpt (mainly styling and the audio pipeline)

import React, { useState, useRef, useEffect } from "react";
import { FaMicrophone, FaStop, FaTrash, FaPlay, FaTimes } from "react-icons/fa";
import "./styles.css";

const API_BASE_URL = process.env.REACT_APP_API_URL;

export default function AudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [transcription, setTranscription] = useState("");
  const [outputData, setOutputData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState("");

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const manuallyStoppedRef = useRef(false);
  useEffect(() => {
    navigator.mediaDevices
      .enumerateDevices()
      .then((devices) => {
        devices.forEach((device) => {
          console.log(device.kind, device.label);
        });
      })
      .catch((err) => {
        console.error("Error enumerating devices:", err);
      });
  }, []);

  const startRecording = async () => {
    manuallyStoppedRef.current = false;
    setErrorMessage("");
    setTranscription(""); 
    try {
      setIsRecording(true);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      // doing this to let me run on non-edge browsers(specifically tested on firefox w/ ubuntu24.04)
      const mimeType = MediaRecorder.isTypeSupported("audio/ogg; codecs=opus")
        ? "audio/ogg; codecs=opus"
        : "audio/webm"; //this is a backup method
      
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      // actually getting the recording
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // wait until it finishes recording(previous iterations stopped too quickly, so added methods to check if the size is too small or if its empty)
      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
      
        if (!manuallyStoppedRef.current) {
          console.warn("Recorder stopped automatically. Skipping upload.");
          setErrorMessage("Recording ended unexpectedly. Try again.");
          setIsRecording(false);
          return;
        }
      
        if (blob.size < 1000) {
          console.warn("Audio blob too small.");
          setErrorMessage("Recording was too short. Try again.");
          setIsRecording(false);
          return;
        }
      
        setAudioBlob(blob);
        setAudioURL(URL.createObjectURL(blob)); // create playback 
        console.log("Recorded audio blob:", blob);
      
        setIsConverting(true);
        try {
          const formData = new FormData();
          formData.append("file", blob, mimeType.includes("ogg") ? "recording.ogg" : "recording.webm");
      
          const response = await fetch(`${API_BASE_URL}/record`, {
            method: "POST",
            body: formData,
          });
      
          if (!response.ok) {
            throw new Error(`HTTP error: status ${response.status}`);
          }
      
          const result = await response.json();
          console.log("Transcription received:", result.transcription);
          setTranscription(result.transcription);
        } catch (uploadError) {
          console.error("Error uploading audio:", uploadError);
          setErrorMessage("Error uploading audio: " + uploadError.message);
        } finally {
          setIsConverting(false);
          setIsRecording(false);
        }
      };
      

      recorder.start();
    } catch (error) {
      console.error("Error accessing microphone:", error); //put this in to log if the microphone input is working or missing. previous versions woudl have issues with audio from the wrong source not reaching the browser, but not tripping an error, so resulted in empty blobs and invalid transcripts
      setErrorMessage("Error accessing microphone: " + error.message);
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    manuallyStoppedRef.current = true;
    mediaRecorderRef.current.stop();

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      
      setIsRecording(false);
    }
  };

  const deleteAudio = () => {
    setTranscription(""); // Clear the transcript, data and any error
    setOutputData(null);  
    setErrorMessage("");   
  };

  const handleOptimize = async () => {
    if (!transcription) {
      setErrorMessage("No transcription found!");
      return;
    }
    setErrorMessage(""); 
    setIsOptimizing(true); 
    try {
      const response = await fetch(`${API_BASE_URL}/optimize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ transcription }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error: status ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Optimization response:", data.schedule);
      setOutputData(data.schedule);
      setShowPopup(true); 
    } catch (optimizeError) {
      console.error("Optimization error:", optimizeError);
      setErrorMessage("Optimization failed: " + optimizeError.message);
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div className="container">
      <header className="navbar">
        <h1>Medical Triaging Optimization System</h1>
      </header>

      <main className="content">
        <p>
          Press start to record voice input, stop to finish the recording and generate a transcipt, and optimize to process the text and add it to our schedule! 
        </p>
        {errorMessage && <p className="error">{errorMessage}</p>}
        <div className="button-container">
          <button
            onClick={startRecording}
            disabled={isRecording || isConverting}
            className="btn btn-record"
          >
            <FaMicrophone /> {isRecording ? "Recording..." : "Start Recording"}
          </button>
          <button
            onClick={stopRecording}
            disabled={!isRecording}
            className="btn btn-rec-stop"
          >
            <FaStop /> Stop Recording
          </button>
          <button
            onClick={deleteAudio}
            disabled={!transcription}
            className="btn btn-abort"
          >
            <FaTrash /> Clear Transcript
          </button>
          <button
            onClick={handleOptimize}
            disabled={isOptimizing || !transcription}
            className="btn btn-process"
          >
            <FaPlay /> {isOptimizing ? "Optimizing..." : "Optimize"}
          </button>
        </div>
        {transcription && (
          <div className="transcript-display">
            <h3>Transcription:</h3>
            <p>{transcription}</p>
          </div>
        )}
        {audioURL && (
      <div className="audio-preview">
       <h4>Playback:</h4>
      <audio controls src={audioURL}></audio>
      </div>
)}
      </main>

      {/* this controls the popup schedule table, with some formatting pulled from the styles.css file*/}
      {showPopup && outputData && (
        <div className="popup">
          <div className="popup-content">
            <div className="popup-header">
              <h2>Schedule Preview</h2>
              <button onClick={() => setShowPopup(false)} className="close-btn">
                <FaTimes />
              </button>
            </div>
            <p>Displaying the new schedule, please verify that all the values are correct before hitting enter!</p>
            <table>
              <thead>
                <tr>
                  <th>Scan ID</th>
                  <th>Scan Type</th>
                  <th>Duration</th>
                  <th>Priority</th>
                  <th>Patient ID</th>
                  <th>Check In Date</th>
                  <th>Check In Time</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {outputData.map((row, index) => (
                  <tr key={index}>
                    <td>{row.scan_id}</td>
                    <td>{row.scan_type}</td>
                    <td>{row.duration}</td>
                    <td>{row.priority}</td>
                    <td>{row.patient_id}</td>
                    <td>{row.check_in_date}</td>
                    <td>{row.check_in_time}</td>
                    <td>{row.machine}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="button-container">
              <button onClick={() => setShowPopup(false)} className="btn btn-close">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
