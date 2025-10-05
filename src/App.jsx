// App.jsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import openaiLogo from "@/assets/OpenAI_Logo.svg.png";
import huggingfaceLogo from "@/assets/Hf-logo-with-title.svg.png";
import pyannoteLogo from "@/assets/logopyannote.png";
import humainLogo from "@/assets/HUMAIN.svg.png";

const API_BASE = import.meta.env.VITE_API_URL || ""; // e.g. http://localhost:8000

export default function App() {
  const [step, setStep] = useState("upload"); // upload | progress | results
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("english");
  const [speakers, setSpeakers] = useState(1);
  const [moderatorFirst, setModeratorFirst] = useState(false);
  const [progress, setProgress] = useState({ transcription: 0, translation: 0 });
  const [transcript, setTranscript] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");

  const startProcessing = async () => {
    if (!file) return;
    setStep("progress");
    setProgress({ transcription: 0, translation: 0 });

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    formData.append("moderator_first", moderatorFirst ? "true" : "false");
    formData.append("speakers", speakers);

    try {
      // simulate frontend progress bar while backend works
      let t = 0;
      const interval = setInterval(() => {
        t += 8;
        setProgress({
          transcription: Math.min(t, 95),
          translation: language === "arabic" ? Math.min(t / 2, 95) : 0,
        });
        if (t >= 95) clearInterval(interval);
      }, 700);

      const res = await fetch(`${API_BASE}/process`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || "Server error");
      }

      const data = await res.json();
      setTranscript(data.text || "");
      setDownloadUrl(API_BASE + data.download_url);
      setProgress({
        transcription: 100,
        translation: language === "arabic" ? 100 : 0,
      });
      setStep("results");
    } catch (err) {
      console.error(err);
      alert("Processing failed: " + (err.message || err));
      setStep("upload");
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-6">
      <Card className="w-full max-w-xl shadow-2xl rounded-2xl mb-8">
        <CardContent className="p-6 space-y-6">
          {/* Upload Step */}
          {step === "upload" && (
            <div className="space-y-4">
              <h1 className="text-2xl font-bold">Upload Audio</h1>
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => setFile(e.target.files[0])}
                className="block w-full border p-2 rounded-lg"
              />
              {file && <p className="text-sm text-gray-600">Selected: {file.name}</p>}

              <div className="space-y-2">
                <label className="block font-medium">Language</label>
                <select
                  className="w-full border p-2 rounded-lg"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="english">English (Transcribe only)</option>
                  <option value="arabic">Arabic (Transcribe + Translate)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="block font-medium">Number of Speakers</label>
                <input
                  type="number"
                  min="1"
                  value={speakers}
                  onChange={(e) => setSpeakers(e.target.value)}
                  className="w-full border p-2 rounded-lg"
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={moderatorFirst}
                  onChange={(e) => setModeratorFirst(e.target.checked)}
                />
                <label>Moderator is the first speaker</label>
              </div>

              <Button onClick={startProcessing} disabled={!file} className="w-full">
                Start Processing
              </Button>
            </div>
          )}

          {/* Progress Step */}
          {step === "progress" && (
            <div className="space-y-4">
              <h1 className="text-2xl font-bold">Processing...</h1>
              <div>
                <p>Transcription</p>
                <Progress value={progress.transcription} />
              </div>
              {language === "arabic" && (
                <div>
                  <p>Translation</p>
                  <Progress value={progress.translation} />
                </div>
              )}
            </div>
          )}

          {/* Results Step */}
          {step === "results" && (
            <div className="space-y-4">
              <h1 className="text-2xl font-bold">Completed!</h1>
              <p className="text-green-600">Your transcript is ready.</p>
              <textarea
                value={transcript}
                readOnly
                className="w-full h-40 border p-2 rounded-lg"
              />
              <a
                href={downloadUrl}
                download="transcript.docx"
                className="block w-full text-center bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 transition"
              >
                Download Transcript
              </a>
            </div>
          )}
        </CardContent>
      </Card>

      {/* --- Powered By Section --- */}
      <footer className="w-full border-t border-gray-200 pt-6 text-center">
        <p className="text-sm font-medium text-gray-600 mb-4">Powered By</p>
        <div className="flex justify-center items-center flex-wrap gap-8">
          <img
            src={openaiLogo}
            alt="OpenAI"
            title="OpenAI"
            className="h-10 object-contain opacity-80 hover:opacity-100 transition-transform duration-200 hover:scale-105"
          />
          <img
            src={huggingfaceLogo}
            alt="HuggingFace"
            title="HuggingFace"
            className="h-10 object-contain opacity-80 hover:opacity-100 transition-transform duration-200 hover:scale-105"
          />
          <img
            src={pyannoteLogo}
            alt="Pyannote"
            title="Pyannote"
            className="h-10 object-contain opacity-80 hover:opacity-100 transition-transform duration-200 hover:scale-105"
          />
          <img
            src={humainLogo}
            alt="HUMAIN"
            title="HUMAIN"
            className="h-10 object-contain opacity-80 hover:opacity-100 transition-transform duration-200 hover:scale-105"
          />
        </div>
      </footer>
    </div>
  );
}
