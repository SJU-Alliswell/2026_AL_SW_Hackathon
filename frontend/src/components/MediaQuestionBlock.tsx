import type { MediaQuestionBlock as MediaQuestionBlockType } from "../types/submission";
import { UploadDropzone } from "./UploadDropzone";

type MediaQuestionBlockProps = {
  index: number;
  block: MediaQuestionBlockType;
  canRemove: boolean;
  onChange: (block: MediaQuestionBlockType) => void;
  onRemove: () => void;
};

export function MediaQuestionBlock({
  index,
  block,
  canRemove,
  onChange,
  onRemove,
}: MediaQuestionBlockProps) {
  return (
    <section className="block">
      <div className="block-header">
        <h2>영상/질문 블록 {index + 1}</h2>
        {canRemove ? (
          <button className="secondary-button" type="button" onClick={onRemove}>
            삭제
          </button>
        ) : null}
      </div>

      <UploadDropzone
        file={block.file}
        onFileChange={(file) => onChange({ ...block, file })}
      />

      <label className="field-label" htmlFor={`question-${block.blockId}`}>
        질문
      </label>
      <textarea
        id={`question-${block.blockId}`}
        className="textarea question-textarea"
        value={block.question}
        onChange={(event) => onChange({ ...block, question: event.target.value })}
        placeholder="질문을 입력하세요."
      />
    </section>
  );
}
