const ACCEPTED_EXTENSIONS = [
  ".mp4",
  ".mov",
  ".webm",
  ".mkv",
  ".avi",
  ".m4a",
  ".mp3",
  ".wav",
  ".aac",
  ".flac",
  ".ogg",
  ".opus",
].join(",");

type UploadDropzoneProps = {
  file: File | null;
  onFileChange: (file: File) => void;
};

export function UploadDropzone({ file, onFileChange }: UploadDropzoneProps) {
  const handleFiles = (files: FileList | null) => {
    const nextFile = files?.[0];
    if (nextFile) {
      onFileChange(nextFile);
    }
  };

  return (
    <label
      className="dropzone"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        handleFiles(event.dataTransfer.files);
      }}
    >
      <input
        className="file-input"
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        onChange={(event) => handleFiles(event.target.files)}
      />
      <span className="dropzone-title">
        {file ? file.name : "영상 또는 음성 파일 선택"}
      </span>
      <span className="dropzone-meta">
        드래그앤드롭 또는 클릭해서 파일을 선택하세요.
      </span>
    </label>
  );
}
