type ResumeInputProps = {
  value: string;
  onChange: (value: string) => void;
};

export function ResumeInput({ value, onChange }: ResumeInputProps) {
  return (
    <section className="section">
      <label className="field-label" htmlFor="resume">
        자기소개서
      </label>
      <textarea
        id="resume"
        className="textarea resume-textarea"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="자기소개서 내용을 붙여넣으세요."
      />
    </section>
  );
}
