import real_ladybug as lbug
import os

class PatientGraphDB:
    def __init__(self, patient_id):
        # Create a dedicated local folder for this specific patient
        os.makedirs("./kg/patients", exist_ok=True)
        self.db_path = f"./kg/patients/patient_{patient_id}_graph.lbug"
        
        print(f"Connecting to local LadybugDB at: {self.db_path}")
        self.db = lbug.Database(self.db_path)
        self.conn = lbug.Connection(self.db)
        
        self._init_schema()

    def _init_schema(self):
        """Initializes the Node and Edge blueprints if they don't exist yet."""
        try:
            # 1. Create the Nodes (Entities)
            self.conn.execute("""
                CREATE NODE TABLE Entity (
                    text STRING, 
                    label STRING, 
                    PRIMARY KEY (text)
                )
            """)
            
            # 2. Create the Edges (Relations with our Epistemic Trackers)
            self.conn.execute("""
                CREATE REL TABLE RELATION (
                    FROM Entity TO Entity, 
                    predicate STRING,
                    proposed_by STRING,
                    patient_acceptance STRING
                )
            """)
            print("New graph schema initialized.")
        except RuntimeError:
            # LadybugDB throws an error if tables already exist, which is expected on subsequent loads
            pass 

    def ingest_bert_payload(self, kg_payload):
            """Merges the ModernBERT JSON output into the patient's graph."""
            
            # 1. Upsert Entities (FIXED CYPHER)
            for entity in kg_payload["entities"]:
                self.conn.execute(
                    "MERGE (e:Entity {text: $text}) SET e.label = $label",
                    parameters={"text": entity["text"], "label": entity["label"]}
                )

            # 2. Upsert Relations
            for rel in kg_payload["relations"]:
                self.conn.execute("""
                    MATCH (source:Entity {text: $src}), (target:Entity {text: $tgt})
                    MERGE (source)-[r:RELATION {
                        predicate: $pred, 
                        proposed_by: $prop, 
                        patient_acceptance: $acc
                    }]->(target)
                """, parameters={
                    "src": rel["source"],
                    "tgt": rel["target"],
                    "pred": rel["predicate"],
                    "prop": rel["proposed_by"],
                    "acc": rel["patient_acceptance"]
                })
            print(f"Successfully ingested {len(kg_payload['relations'])} relations.")