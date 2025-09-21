// App.jsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";

const API_BASE = import.meta.env.VITE_API_URL || ""; // e.g. http://localhost:8000

export default function App() {
  const [step, setStep] = useState("upload"); // upload | progress | results
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("english");
  const [speakers, setSpeakers] = useState(1);
  const [moderatorFirst, setModeratorFirst] = useState(false);
  const [progress, setProgress] = useState({ transcription: 0, translation: 0 });
  const [transcript, setTranscript] = useState("");

  // Mock backend call
  const startProcessing = async () => {
  setStep("progress");
  setProgress({ transcription: 0, translation: 0 });

  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language);
  formData.append("moderator_first", moderatorFirst ? "true" : "false");
  formData.append("speakers", speakers);

  try {
    // still keep a simple fake progress indicator for UX while request runs
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
    // data.text is the plain transcript for preview
    setTranscript(data.text || ""); 
    // set progress to finished
    setProgress({ transcription: 100, translation: language === "arabic" ? 100 : 0 });
    setStep("results");

    // Save download info in state
    setDownloadUrl(API_BASE + data.download_url); // e.g. http://localhost:8000/download/<name>
  } catch (err) {
    console.error(err);
    alert("Processing failed: " + (err.message || err));
    setStep("upload");
  }
};

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
      <Card className="w-full max-w-xl shadow-2xl rounded-2xl">
        <CardContent className="p-6 space-y-6">
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

          {step === "results" && (
            <div className="space-y-4">
              <h1 className="text-2xl font-bold">Results</h1>
              <textarea
                value={transcript}
                readOnly
                className="w-full h-40 border p-2 rounded-lg"
              />
              <Button
                onClick={async () => {
                  try {
                    // Call your backend endpoint (this assumes you have a `/process` route that returns a DOCX)
                    const response = await fetch("http://localhost:5000/process", {
                      method: "POST",
                      body: JSON.stringify({
                        language,
                        speakers,
                        moderatorFirst,
                        // you’ll need to include audio upload earlier and pass the file ref here
                      }),
                      headers: { "Content-Type": "application/json" },
                    });

                    // Get blob (docx file)
                    const blob = await response.blob();

                    // Trigger download
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "transcript.docx"; // instead of transcript.txt
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch (err) {
                    console.error("Download failed", err);
                  }
                }}
                className="w-full"
                >
                Download Transcript
                </Button>

            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
