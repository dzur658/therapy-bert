const REP_API_BASE = "http://127.0.0.1:8087";

export interface AnalyzeRequest {
  transcript: string;
  reveal: string;
}

export interface AnalyzeResponse {
  baseline: string;
  insight: string;
  processing_time_seconds: number;
}

export const RepresentationService = {
  async analyze(transcript: string, reveal: string): Promise<AnalyzeResponse> {
    const res = await fetch(`${REP_API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript, reveal } satisfies AnalyzeRequest),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      let message = `Representation analysis failed: ${res.status}`;
      if (typeof err === "object" && err !== null && "detail" in err) {
        const d = (err as { detail: unknown }).detail;
        if (typeof d === "string") message = d;
        else if (Array.isArray(d)) message = d.map(String).join("; ");
        else if (d != null) message = String(d);
      }
      throw new Error(message);
    }
    return res.json();
  },
};
