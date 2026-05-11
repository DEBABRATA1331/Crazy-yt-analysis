"use client";

import { useState } from "react";

export default function Home() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const analyzeSentiment = async () => {
    if (!text.trim()) return;

    setLoading(true);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/predict`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: text,
          }),
        }
      );

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error(error);
      alert("Failed to connect backend");
    }

    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <h1 className="text-5xl font-bold text-center mb-3">
          Crazy YT Analysis
        </h1>

        <p className="text-center text-zinc-400 mb-10">
          AI Powered YouTube Sentiment Analyzer
        </p>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter YouTube comment..."
          className="w-full h-40 rounded-xl bg-zinc-900 border border-zinc-700 p-4 text-white outline-none"
        />

        <button
          onClick={analyzeSentiment}
          disabled={loading}
          className="w-full mt-5 bg-red-600 hover:bg-red-700 transition-all py-4 rounded-xl text-lg font-semibold"
        >
          {loading ? "Analyzing..." : "Analyze Sentiment"}
        </button>

        {result && (
          <div className="mt-10 bg-zinc-900 border border-zinc-700 rounded-xl p-6">
            <h2 className="text-2xl font-bold mb-4">
              Analysis Result
            </h2>

            <p className="mb-2">
              <span className="font-semibold">Sentiment:</span>{" "}
              {result.sentiment}
            </p>

            <p className="mb-2">
              <span className="font-semibold">Confidence:</span>{" "}
              {(result.confidence * 100).toFixed(2)}%
            </p>

            <p className="mt-4 text-zinc-400">
              "{result.text}"
            </p>
          </div>
        )}
      </div>
    </main>
  );
}