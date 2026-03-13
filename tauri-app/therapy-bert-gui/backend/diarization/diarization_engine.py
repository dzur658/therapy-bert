from pyannote.audio import Pipeline
import torch
import gc
from faster_whisper import WhisperModel

class DiarizationEngine:
    def __init__(self, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        compute_type = "float16" if torch.cuda.is_available() else "float32"

        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-community-1").to(torch.device(self.device))
        self.asr_pipeline = WhisperModel("distil-whisper/distil-large-v3.5-ct2", device=self.device, compute_type=compute_type)

    def diarize_and_transcribe(self, audio_file_path):
        def _build_diarized_transcript(diarization_output, whisper_segments):
            """
            Merges Pyannote speaker segments with Faster-Whisper word timestamps.
            """

            def _normalize_speaker_label(speaker_id: str) -> str:
                # bogus initialization to handle the "UNKNOWN" case
                speaker_num = 9

                if speaker_id.startswith("SPEAKER_"):
                    speaker_num = int(speaker_id.split("_")[1])
                    speaker_num += 1
                
                return "SPEAKER_0" + str(speaker_num)

            # 1. Map the Pyannote "parking spaces"
            speaker_turns = []
            for turn, _, speaker in diarization_output.itertracks(yield_label=True):
                # print(turn.start, turn.end, speaker)
                speaker_turns.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
                
            final_transcript = []
            current_speaker = None
            current_phrase = []
            
            # 2. Unpack the Whisper objects
            for segment in whisper_segments:
                for word in segment.words:
                    # Find the exact middle of the word
                    word_midpoint = (word.start + word.end) / 2
                    assigned_speaker = "UNKNOWN"
                    
                    # 3. Check which speaker's block the word's midpoint falls into
                    for turn in speaker_turns:
                        if turn["start"] <= word_midpoint <= turn["end"]:
                            assigned_speaker = turn["speaker"]
                            break
                    
                    # 4. Group words back into sentences based on the speaker
                    if assigned_speaker != current_speaker:
                        # If the speaker changes, save the old sentence and start a new one
                        if current_phrase:
                            final_transcript.append({
                                "speaker": _normalize_speaker_label(current_speaker),
                                "text": "".join(current_phrase).strip()
                            })
                        current_speaker = assigned_speaker
                        current_phrase = [word.word]
                    else:
                        # If it's the same speaker, just append the word
                        current_phrase.append(word.word)
                        
            # 5. Catch the very last sentence when the audio ends
            if current_phrase:
                final_transcript.append({
                    "speaker": _normalize_speaker_label(current_speaker),
                    "text": "".join(current_phrase).strip()
                })
                
            return final_transcript

        # 1. Run diarization and ASR in parallel
        diarization_output = self.diarization_pipeline(audio_file_path)
        
        # dump cache and call gc to guard against OOM
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
        elif self.device == "mps":
            torch.mps.empty_cache()
        
        whisper_segments, _ = self.asr_pipeline.transcribe(audio_file_path, beam_size=5, language="en", word_timestamps=True)

        get_transcript = _build_diarized_transcript(diarization_output.speaker_diarization, whisper_segments)

        # clean up before returning
        gc.collect()
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        return {"transcript": get_transcript}
    
if __name__ == "__main__":
    AUDIO_FILE_TEST_PATH = "/home/dzur/ai_projects/new_jh_test.wav"

    engine = DiarizationEngine()

    print(engine.diarize_and_transcribe(AUDIO_FILE_TEST_PATH))