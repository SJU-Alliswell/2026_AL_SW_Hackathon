import { useMemo, useState } from "react";

import { analyzeSubmission, createSubmission, createVirtualUser } from "./api/submissions";
import { uploadFileMultipart } from "./api/uploads";
import { AddBlockButton } from "./components/AddBlockButton";
import { MediaQuestionBlock } from "./components/MediaQuestionBlock";
import { ResultPanel } from "./components/ResultPanel";
import { ResumeInput } from "./components/ResumeInput";
import type { AnalyzeResult, MediaQuestionBlock as MediaQuestionBlockType } from "./types/submission";

function createBlock(): MediaQuestionBlockType {
  return {
    blockId: crypto.randomUUID(),
    file: null,
    question: "",
  };
}

export default function App() {
  const [resume, setResume] = useState("");
  const [blocks, setBlocks] = useState<MediaQuestionBlockType[]>([createBlock()]);
  const [virtualUserId, setVirtualUserId] = useState<string | null>(null);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [results, setResults] = useState<AnalyzeResult[]>([]);
  const [status, setStatus] = useState("입력 대기 중");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = useMemo(
    () =>
      resume.trim().length > 0 &&
      blocks.every((block) => block.file && block.question.trim().length > 0),
    [blocks, resume],
  );

  const updateBlock = (nextBlock: MediaQuestionBlockType) => {
    setBlocks((current) =>
      current.map((block) =>
        block.blockId === nextBlock.blockId ? nextBlock : block,
      ),
    );
  };

  const removeBlock = (blockId: string) => {
    setBlocks((current) => current.filter((block) => block.blockId !== blockId));
  };

  const handleSubmit = async () => {
    if (!canSubmit || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setResults([]);

    try {
      setStatus("사용자와 제출 정보를 준비하는 중");
      const nextVirtualUserId = virtualUserId ?? (await createVirtualUser());
      const nextSubmissionId =
        submissionId ?? (await createSubmission(nextVirtualUserId));
      setVirtualUserId(nextVirtualUserId);
      setSubmissionId(nextSubmissionId);

      setStatus("파일을 MinIO에 업로드하는 중");
      const uploadedBlocks: MediaQuestionBlockType[] = [];
      for (const block of blocks) {
        if (!block.file) {
          continue;
        }
        const upload = block.upload?.completed
          ? block.upload
          : await uploadFileMultipart({
              virtualUserId: nextVirtualUserId,
              submissionId: nextSubmissionId,
              blockId: block.blockId,
              file: block.file,
            });

        uploadedBlocks.push({
          ...block,
          upload: {
            objectKey: upload.objectKey,
            uploadId: upload.uploadId,
            completed: true,
          },
        });
      }

      setBlocks(uploadedBlocks);
      setStatus("분석 요청 중");
      const nextResults = await analyzeSubmission({
        virtualUserId: nextVirtualUserId,
        submissionId: nextSubmissionId,
        resume,
        blocks: uploadedBlocks,
      });
      setResults(nextResults);
      setStatus("분석 완료");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "처리 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1>HACA 발표/면접 피드백</h1>
        <span>{status}</span>
      </header>

      <ResumeInput value={resume} onChange={setResume} />

      <div className="blocks">
        {blocks.map((block, index) => (
          <MediaQuestionBlock
            block={block}
            canRemove={blocks.length > 1}
            index={index}
            key={block.blockId}
            onChange={updateBlock}
            onRemove={() => removeBlock(block.blockId)}
          />
        ))}
      </div>

      <AddBlockButton onClick={() => setBlocks((current) => [...current, createBlock()])} />

      <div className="actions">
        <button
          className="primary-button"
          disabled={!canSubmit || isSubmitting}
          type="button"
          onClick={handleSubmit}
        >
          분석 시작
        </button>
      </div>

      <ResultPanel results={results} />
    </main>
  );
}
