/**
 * TranscriptManager - Manages session transcripts via the sqlite_helper_api.
 * Uses HTTP for Phase 1/2; will switch to Tauri invoke in Phase 3.
 */

const SQLITE_API_BASE = "http://127.0.0.1:8088";

export interface TranscriptLine {
  speaker: string;
  text: string;
}

export interface DbSession {
  id: string;
  patient_id: string;
  created_at: string;
  transcript_json: string;
}

export const TranscriptManager = {
  async init(): Promise<void> {
    // No-op: sqlite service is assumed running (Option A)
  },

  async getSessionsForPatient(patientId: string): Promise<DbSession[]> {
    const res = await fetch(`${SQLITE_API_BASE}/db/sqlite/sessions/${encodeURIComponent(patientId)}`);
    if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`);
    const json = await res.json();
    if (json.status !== "success" || !Array.isArray(json.data)) {
      return [];
    }
    return json.data.map((d: { session_id: string; date: string; transcript: unknown }) => ({
      id: d.session_id,
      patient_id: patientId,
      created_at: d.date,
      transcript_json: JSON.stringify({ transcript: d.transcript }),
    }));
  },

  async saveTranscript(
    patientId: string,
    _patientName: string,
    lines: TranscriptLine[],
    audioFilePath = ""
  ): Promise<string> {
    const sessionId = crypto.randomUUID();
    const res = await fetch(`${SQLITE_API_BASE}/db/sqlite/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        patient_id: patientId,
        audio_file_path: audioFilePath,
        transcript_data: { transcript: lines },
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `Failed to save transcript: ${res.status}`);
    }
    return sessionId;
  },

  async persistTranscript(sessionId: string, lines: TranscriptLine[]): Promise<void> {
    const res = await fetch(`${SQLITE_API_BASE}/db/sqlite/sessions/${encodeURIComponent(sessionId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript_data: { transcript: lines } }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `Failed to update transcript: ${res.status}`);
    }
  },

  async deleteSession(sessionId: string): Promise<void> {
    const res = await fetch(`${SQLITE_API_BASE}/db/sqlite/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `Failed to delete session: ${res.status}`);
    }
  },
};
