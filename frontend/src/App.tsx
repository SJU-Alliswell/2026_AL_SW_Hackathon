import { useEffect, useMemo, useState } from "react";

import { analyzeSubmission, createSubmission, createVirtualUser } from "./api/submissions";
import { uploadFileMultipart } from "./api/uploads";
import { AddBlockButton } from "./components/AddBlockButton";
import { MediaQuestionBlock } from "./components/MediaQuestionBlock";
import { ResultPanel } from "./components/ResultPanel";
import { ResumeInput } from "./components/ResumeInput";
import type { AnalyzeResult, MediaQuestionBlock as MediaQuestionBlockType } from "./types/submission";

function createClientId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = Math.floor(Math.random() * 16);
    const value = char === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function createBlock(): MediaQuestionBlockType {
  return {
    blockId: createClientId(),
    file: null,
    question: "",
  };
}

type ProgressPhase = "idle" | "preparing" | "uploading" | "analyzing" | "complete" | "error";

type ProgressState = {
  phase: ProgressPhase;
  label: string;
  percent: number;
  detail?: string;
};

const IDLE_PROGRESS: ProgressState = { phase: "idle", label: "", percent: 0 };

export default function App() {
  const [resume, setResume] = useState("");
  const [blocks, setBlocks] = useState<MediaQuestionBlockType[]>([createBlock()]);
  const [virtualUserId, setVirtualUserId] = useState<string | null>(null);
  const [submissionId, setSubmissionId] = useState<string | null>(null);
  const [results, setResults] = useState<AnalyzeResult[]>([]);
  const [progress, setProgress] = useState<ProgressState>(IDLE_PROGRESS);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canSubmit = useMemo(
    () =>
      resume.trim().length > 0 &&
      blocks.every((block) => block.file && block.question.trim().length > 0),
    [blocks, resume],
  );


  useEffect(() => {
    if (progress.phase !== "analyzing") {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setProgress((current) => {
        if (current.phase !== "analyzing") {
          return current;
        }
        return { ...current, percent: Math.min(current.percent + 1, 94) };
      });
    }, 1200);

    return () => window.clearInterval(intervalId);
  }, [progress.phase]);

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
    setProgress({ phase: "preparing", label: "제출 정보 준비 중", percent: 8 });

    try {
      const nextVirtualUserId = virtualUserId ?? (await createVirtualUser());
      const nextSubmissionId =
        submissionId ?? (await createSubmission(nextVirtualUserId));
      setVirtualUserId(nextVirtualUserId);
      setSubmissionId(nextSubmissionId);

      const uploadableBlocks = blocks.filter((block) => block.file);
      const totalUploadBytes = uploadableBlocks.reduce(
        (total, block) => total + (block.file?.size ?? 0),
        0,
      );
      let completedUploadBytes = 0;
      setProgress({
        phase: "uploading",
        label: "파일 업로드 중",
        percent: 15,
        detail: `${uploadableBlocks.length}개 파일을 업로드하고 있습니다.`,
      });

      const uploadedBlocks: MediaQuestionBlockType[] = [];
      for (const [uploadIndex, block] of blocks.entries()) {
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
              onProgress: ({ uploadedBytes }) => {
                const uploadedTotal = completedUploadBytes + uploadedBytes;
                const uploadRatio = totalUploadBytes > 0 ? uploadedTotal / totalUploadBytes : 1;
                setProgress({
                  phase: "uploading",
                  label: "파일 업로드 중",
                  percent: Math.min(70, 15 + Math.round(uploadRatio * 55)),
                  detail: `${uploadIndex + 1}/${uploadableBlocks.length} 파일 업로드 중`,
                });
              },
            });

        completedUploadBytes += block.file.size;

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
      setProgress({
        phase: "analyzing",
        label: "텍스트 변환 중",
        percent: 78,
        detail: "영상에서 음성을 추출해 텍스트로 변환하고 있습니다.",
      });
      const nextResults = await analyzeSubmission({
        virtualUserId: nextVirtualUserId,
        submissionId: nextSubmissionId,
        resume,
        blocks: uploadedBlocks,
      });
      setResults(nextResults);
      setProgress({ phase: "complete", label: "분석 완료", percent: 100 });
    } catch (error) {
      setProgress({
        phase: "error",
        label: error instanceof Error ? error.message : "처리 중 오류가 발생했습니다.",
        percent: 100,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1 className="brand-title">
          <span className="brand-accent">MY INT</span>erviewer
        </h1>
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

      {progress.phase !== "idle" && (
        <section className={`progress-panel progress-${progress.phase}`} aria-live="polite">
          <div className="progress-header">
            <span>{progress.label}</span>
            <strong>{progress.percent}%</strong>
          </div>
          <div className="progress-track">
            <div
              className="progress-bar"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
          {progress.detail && <p>{progress.detail}</p>}
        </section>
      )}

      <ResultPanel results={results} />
    </main>
  );
}
