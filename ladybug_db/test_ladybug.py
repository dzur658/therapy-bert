from db_manager import PatientGraphDB

# 1. Simulate the output from your Master Inference Script
mock_bert_output = {
    "entities": [
        {"text": "mother's criticism", "label": "Trigger"},
        {"text": "anxiety", "label": "Symptom"},
        {"text": "deep breathing", "label": "Coping_Mechanism"}
    ],
    "relations": [
        {
            "source": "mother's criticism",
            "predicate": "CAUSES",
            "target": "anxiety",
            "proposed_by": "Therapist",
            "patient_acceptance": "Denied"
        },
        {
            "source": "deep breathing",
            "predicate": "IMPROVES",
            "target": "anxiety",
            "proposed_by": "Patient",
            "patient_acceptance": "Affirmed"
        }
    ]
}

# 2. Spin up a database for "Patient_001"
print("--- INITIALIZING DB ---")
db = PatientGraphDB(patient_id="001")

# 3. Ingest the data
print("\n--- INGESTING DATA ---")
db.ingest_bert_payload(mock_bert_output)

# 4. Test the Query! 
print("\n--- QUERYING THE GRAPH ---")
# Let's ask the DB: "Show me all triggers the therapist proposed that the patient denied."
query = """
    MATCH (trigger:Entity)-[r:RELATION]->(symptom:Entity)
    WHERE r.proposed_by = 'Therapist' AND r.patient_acceptance = 'Denied'
    RETURN trigger.text AS Trigger, r.predicate AS Connection, symptom.text AS Symptom
"""

results = db.conn.execute(query)

while results.has_next():
    row = results.get_next()
    print(f"Clinical Insight Found: The therapist thought '{row[0]}' {row[1]} '{row[2]}', but the patient denied it.")