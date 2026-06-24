import { apiRequest } from "./client";
import type { AnalyzeResult, MediaQuestionBlock } from "../types/submission";

export async function createVirtualUser(): Promise<string> {
  const response = await apiRequest<{ virtual_user_id: string }>("/virtual-users", {
    method: "POST",
    body: JSON.stringify({}),
  });
  return response.virtual_user_id;
}

export async function createSubmission(virtualUserId: string): Promise<string> {
  const response = await apiRequest<{ submission_id: string }>("/submissions", {
    method: "POST",
    body: JSON.stringify({ virtual_user_id: virtualUserId }),
  });
  return response.submission_id;
}

export async function analyzeSubmission(params: {
  virtualUserId: string;
  submissionId: string;
  resume: string;
  blocks: MediaQuestionBlock[];
}): Promise<AnalyzeResult[]> {
  const response = await apiRequest<{
    submission_id: string;
    status: string;
    results: AnalyzeResult[];
  }>(`/submissions/${params.submissionId}/analyze`, {
    method: "POST",
    body: JSON.stringify({
      virtual_user_id: params.virtualUserId,
      resume: params.resume,
      blocks: params.blocks.map((block) => ({
        block_id: block.blockId,
        media_object_key: block.upload?.objectKey,
        question: block.question,
      })),
    }),
  });
  return response.results;
}
