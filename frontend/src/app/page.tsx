"use client";

import { useState, useEffect } from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------- Types ----------------
interface VideoDetails {
  id: string;
  title: string;
  description: string;
  channel_title: string;
  channel_id: string;
  published_at: string;
  thumbnail: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  tags: string[];
}

interface Analytics {
  total_analyzed: number;
  positive_count: number;
  negative_count: number;
  sentiment_score: number;
  engagement_rate: number;
  confidence_distribution: Record<string, number>;
}

interface CommentResult {
  id: string;
  author: string;
  text: string;
  sentiment: string;
  confidence: number;
  like_count: number;
  published_at: string;
}

interface AnalysisResult {
  video: VideoDetails;
  analytics: Analytics;
  comments: CommentResult[];
}

// ---------------- Helpers ----------------
const formatNumber = (n: number): string => {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toString();
};

const formatDate = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
};

// ---------------- Component ----------------
export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingSeconds, setLoadingSeconds] = useState(0);
  const [filter, setFilter] = useState<"all" | "Positive" | "Negative">("all");

  // Loading timer for cold-start UX
  useEffect(() => {
    if (!loading) {
      setLoadingSeconds(0);
      return;
    }
    const interval = setInterval(() => setLoadingSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [loading]);

  const handleAnalyze = async () => {
    if (!url.trim()) {
      setError("Please enter a YouTube URL");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${response.status}`);
      }
      const data: AnalysisResult = await response.json();
      setResult(data);
    } catch (err) {
      console.error("API call failed:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to backend. The server may be sleeping — try again in 30 seconds."
      );
    } finally {
      setLoading(false);
    }
  };

  const pieData = result
    ? [
      { name: "Positive", value: result.analytics.positive_count },
      { name: "Negative", value: result.analytics.negative_count },
    ]
    : [];

  const confData = result
    ? Object.entries(result.analytics.confidence_distribution).map(
      ([range, count]) => ({ range: range + "%", count })
    )
    : [];

  const filteredComments =
    result?.comments.filter((c) =>
      filter === "all" ? true : c.sentiment === filter
    ) ?? [];

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <header className="text-center mb-12">
          <h1 className="text-5xl sm:text-6xl font-bold bg-gradient-to-r from-red-500 via-pink-500 to-purple-500 bg-clip-text text-transparent">
            Crazy YT Analysis
          </h1>
          <p className="mt-3 text-slate-400 text-lg">
            AI-powered YouTube sentiment dashboard
          </p>
        </header>

        {/* Input */}
        <div className="max-w-3xl mx-auto mb-12">
          <div className="flex flex-col sm:flex-row gap-3">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !loading && handleAnalyze()}
              placeholder="Paste any YouTube video link..."
              className="flex-1 px-5 py-4 bg-slate-800/60 backdrop-blur border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/30 transition"
              disabled={loading}
            />
            <button
              onClick={handleAnalyze}
              disabled={loading}
              className="px-8 py-4 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 disabled:from-slate-700 disabled:to-slate-700 disabled:cursor-not-allowed rounded-xl font-semibold transition shadow-lg shadow-red-600/30"
            >
              {loading ? "Analyzing..." : "Analyze Video"}
            </button>
          </div>

          {loading && (
            <div className="mt-4 p-4 bg-slate-800/40 border border-slate-700 rounded-lg text-center text-slate-300">
              <div className="animate-pulse">
                {loadingSeconds < 5
                  ? "Fetching video data..."
                  : loadingSeconds < 15
                    ? "Analyzing comments with ML model..."
                    : "Backend is waking up (free tier sleeps after inactivity) — this can take up to 60s on the first request..."}
              </div>
              <div className="text-xs text-slate-500 mt-1">{loadingSeconds}s</div>
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 bg-red-950/50 border border-red-700 rounded-lg text-red-200">
              ⚠️ {error}
            </div>
          )}
        </div>

        {/* Dashboard */}
        {result && (
          <div className="space-y-8 animate-in fade-in duration-500">
            {/* Video Info Card */}
            <div className="bg-slate-800/40 backdrop-blur border border-slate-700 rounded-2xl overflow-hidden shadow-xl">
              <div className="grid md:grid-cols-2 gap-0">
                <div className="aspect-video bg-slate-900 relative">
                  {result.video.thumbnail && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={result.video.thumbnail}
                      alt={result.video.title}
                      className="w-full h-full object-cover"
                    />
                  )}
                  <a
                    href={`https://youtube.com/watch?v=${result.video.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 hover:opacity-100 transition"
                  >
                    <div className="bg-red-600 rounded-full p-4 shadow-2xl">
                      <svg
                        className="w-8 h-8 text-white"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>
                  </a>
                </div>
                <div className="p-6 flex flex-col justify-between">
                  <div>
                    <h2 className="text-2xl font-bold mb-2 line-clamp-2">
                      {result.video.title}
                    </h2>
                    <p className="text-slate-400 mb-3">
                      📺 {result.video.channel_title}
                    </p>
                    <p className="text-sm text-slate-500 mb-4">
                      Published: {formatDate(result.video.published_at)}
                    </p>
                    <p className="text-sm text-slate-300 line-clamp-3">
                      {result.video.description}
                    </p>
                  </div>
                  {result.video.tags && result.video.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-4">
                      {result.video.tags.slice(0, 6).map((tag, i) => (
                        <span
                          key={i}
                          className="px-2 py-1 bg-slate-700/60 text-xs rounded-full text-slate-300"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                label="Views"
                value={formatNumber(result.video.view_count)}
                icon="👁️"
                color="from-blue-600 to-cyan-600"
              />
              <StatCard
                label="Likes"
                value={formatNumber(result.video.like_count)}
                icon="👍"
                color="from-green-600 to-emerald-600"
              />
              <StatCard
                label="Comments"
                value={formatNumber(result.video.comment_count)}
                icon="💬"
                color="from-purple-600 to-pink-600"
              />
              <StatCard
                label="Engagement"
                value={result.analytics.engagement_rate.toFixed(2) + "%"}
                icon="⚡"
                color="from-orange-600 to-red-600"
              />
            </div>

            {/* Sentiment Score Banner */}
            <div className="bg-gradient-to-r from-slate-800/60 to-slate-700/60 backdrop-blur border border-slate-600 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-slate-400 text-sm uppercase tracking-wider">
                    Overall Sentiment Score
                  </p>
                  <p className="text-4xl font-bold mt-1">
                    {result.analytics.sentiment_score}%
                    <span className="text-lg font-normal text-slate-400 ml-2">
                      positive
                    </span>
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-slate-400">Analyzed</p>
                  <p className="text-2xl font-bold">
                    {result.analytics.total_analyzed} comments
                  </p>
                </div>
              </div>
              <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all"
                  style={{ width: `${result.analytics.sentiment_score}%` }}
                />
              </div>
            </div>

            {/* Charts Grid */}
            <div className="grid lg:grid-cols-2 gap-6">
              {/* Pie chart */}
              <div className="bg-slate-800/40 backdrop-blur border border-slate-700 rounded-2xl p-6">
                <h3 className="text-lg font-semibold mb-4">
                  Sentiment Distribution
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${name} ${(percent! * 100).toFixed(0)}%`
                      }
                    >
                      <Cell fill="#10b981" />
                      <Cell fill="#ef4444" />
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "1px solid #475569",
                        borderRadius: "8px",
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Bar chart */}
              <div className="bg-slate-800/40 backdrop-blur border border-slate-700 rounded-2xl p-6">
                <h3 className="text-lg font-semibold mb-4">
                  Model Confidence Distribution
                </h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={confData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="range" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1e293b",
                        border: "1px solid #475569",
                        borderRadius: "8px",
                      }}
                    />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Comments */}
            <div className="bg-slate-800/40 backdrop-blur border border-slate-700 rounded-2xl p-6">
              <div className="flex flex-wrap items-center justify-between mb-4 gap-2">
                <h3 className="text-lg font-semibold">
                  Top Comments ({filteredComments.length})
                </h3>
                <div className="flex gap-2">
                  <FilterBtn
                    active={filter === "all"}
                    onClick={() => setFilter("all")}
                  >
                    All
                  </FilterBtn>
                  <FilterBtn
                    active={filter === "Positive"}
                    onClick={() => setFilter("Positive")}
                  >
                    👍 Positive
                  </FilterBtn>
                  <FilterBtn
                    active={filter === "Negative"}
                    onClick={() => setFilter("Negative")}
                  >
                    👎 Negative
                  </FilterBtn>
                </div>
              </div>
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                {filteredComments.length === 0 ? (
                  <p className="text-center text-slate-500 py-8">
                    No comments match this filter.
                  </p>
                ) : (
                  filteredComments.map((c) => (
                    <CommentCard key={c.id} comment={c} />
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

// ---------------- Sub-components ----------------

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: string;
  color: string;
}) {
  return (
    <div className="bg-slate-800/40 backdrop-blur border border-slate-700 rounded-2xl p-5 hover:border-slate-600 transition">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-400 text-sm">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div
          className={`w-10 h-10 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center text-lg`}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}

function FilterBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${active
          ? "bg-red-600 text-white"
          : "bg-slate-700/60 text-slate-300 hover:bg-slate-700"
        }`}
    >
      {children}
    </button>
  );
}

function CommentCard({ comment }: { comment: CommentResult }) {
  const isPositive = comment.sentiment === "Positive";
  return (
    <div
      className={`p-4 rounded-lg border ${isPositive
          ? "border-green-700/50 bg-green-950/20"
          : "border-red-700/50 bg-red-950/20"
        }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm font-bold">
            {comment.author.charAt(0).toUpperCase()}
          </div>
          <span className="font-medium text-slate-200">{comment.author}</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 text-xs rounded-full font-semibold ${isPositive
                ? "bg-green-600/30 text-green-300"
                : "bg-red-600/30 text-red-300"
              }`}
          >
            {comment.sentiment} {(comment.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <p
        className="text-sm text-slate-300 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: comment.text }}
      />
      {comment.like_count > 0 && (
        <div className="mt-2 text-xs text-slate-500">
          👍 {formatNumber(comment.like_count)}
        </div>
      )}
    </div>
  );
}
