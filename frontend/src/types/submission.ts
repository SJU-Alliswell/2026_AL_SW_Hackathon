export type MediaQuestionBlock = {
  blockId: string;
  file: File | null;
  question: string;
  upload?: {
    objectKey: string;
    uploadId: string;
    completed: boolean;
  };
};

export type SubmissionFormState = {
  virtualUserId: string;
  submissionId: string;
  resume: string;
  blocks: MediaQuestionBlock[];
};

export type AnalyzeResult = {
  block_id: string;
  media_type: string | null;
  metrics: {
    speech_rate_eojeol_per_minute: number | null;
    filler_word_count: number | null;
    silence_count: number | null;
    gaze_off_count: number | null;
  };
  original_text: string | null;
  cleaned_text: string | null;
  feedback: string | null;
};
