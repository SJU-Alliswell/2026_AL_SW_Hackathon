import type { AnalyzeResult } from "../types/submission";

type ResultPanelProps = {
  results: AnalyzeResult[];
};

export function ResultPanel({ results }: ResultPanelProps) {
  if (results.length === 0) {
    return null;
  }

  return (
    <section className="section results">
      <h2>분석 결과</h2>
      {results.map((result, index) => (
        <article className="result-item" key={result.block_id}>
          <h3>블록 {index + 1}</h3>
          <dl className="metrics">
            <div>
              <dt>발화 속도</dt>
              <dd>{result.metrics.speech_rate_eojeol_per_minute ?? "-"}</dd>
            </div>
            <div>
              <dt>습관어</dt>
              <dd>{result.metrics.filler_word_count ?? "-"}</dd>
            </div>
            <div>
              <dt>침묵 구간</dt>
              <dd>{result.metrics.silence_count ?? "-"}</dd>
            </div>
            <div>
              <dt>시선 이탈</dt>
              <dd>{result.metrics.gaze_off_count ?? "-"}</dd>
            </div>
          </dl>
          <p className="feedback">{result.feedback ?? "피드백 생성 전입니다."}</p>
        </article>
      ))}
    </section>
  );
}
