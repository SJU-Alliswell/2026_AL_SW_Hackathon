const ACCEPTED_EXTENSIONS = [
  ".mp4",
  ".mov",
  ".webm",
  ".mkv",
  ".avi",
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
      {file ? (
        <span className="dropzone-title">{file.name}</span>
      ) : (
        <span className="dropzone-plus" aria-hidden="true">+</span>
      )}
    </label>
  );
}
