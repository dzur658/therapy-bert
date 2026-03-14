/**
 * PatientService - Manages patients via the sqlite_helper_api.
 */

const SQLITE_API_BASE = "http://127.0.0.1:8088";

export interface DbPatient {
  id: string;
  name: string;
  created_at: string;
  session_count: number;
  last_session: string | null;
}

export const PatientService = {
  async getPatients(): Promise<DbPatient[]> {
    const res = await fetch(`${SQLITE_API_BASE}/db/sqlite/patients`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `Failed to fetch patients: ${res.status}`);
    }
    const json = await res.json();
    if (json.status !== "success" || !Array.isArray(json.data)) {
      return [];
    }
    return json.data;
  },

  async createPatient(name: string): Promise<{ id: string; name: string }> {
    const res = await fetch(`${SQLITE_API_BASE}/db/sqlite/patients`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `Failed to create patient: ${res.status}`);
    }
    const json = await res.json();
    if (json.status !== "success" || !json.data) {
      throw new Error("Invalid response from create patient");
    }
    return json.data;
  },

  async deletePatient(id: string): Promise<void> {
    const res = await fetch(
      `${SQLITE_API_BASE}/db/sqlite/patients/${encodeURIComponent(id)}`,
      { method: "DELETE" }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `Failed to delete patient: ${res.status}`);
    }
  },
};
