import type { AnalyzeResult } from "../types/submission";

type ResultPanelProps = {
  results: AnalyzeResult[];
};

type MetricGaugeProps = {
  label: string;
  value: number | null;
  unit: string;
  min: number;
  center: number;
  max: number;
  precision?: number;
  detail?: string;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function formatMetricValue(value: number | null, precision = 0) {
  if (value === null || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(precision);
}

function MetricGauge({
  label,
  value,
  unit,
  min,
  center,
  max,
  precision = 0,
  detail,
}: MetricGaugeProps) {
  const markerPosition =
    value === null || Number.isNaN(value)
      ? 50
      : clamp(((value - min) / (max - min)) * 100, 0, 100);

  return (
    <div className="metric-card metric-gauge">
      <dt>{label}</dt>
      <dd>
        <span className="metric-value">{formatMetricValue(value, precision)}</span>
        <span className="metric-unit">{unit}</span>
      </dd>
      <div className="metric-gradient" aria-hidden="true">
        <span className="metric-marker" style={{ left: `${markerPosition}%` }} />
      </div>
      <div className="metric-center-value">{center}</div>
      {detail && <p>{detail}</p>}
    </div>
  );
}

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
            <MetricGauge
              label="발화 속도"
              value={result.metrics.speech_rate_eojeol_per_minute}
              unit="어절/분"
              min={80}
              center={140}
              max={200}
              precision={0}
            />
            <MetricGauge
              label="습관어 빈도"
              value={result.metrics.filler_word_count}
              unit="개"
              min={0}
              center={3}
              max={6}
              precision={0}
            />
            <MetricGauge
              label="침묵 시간"
              value={result.metrics.silence_total_seconds}
              unit="초"
              min={0}
              center={1}
              max={2}
              precision={1}
            />
            <div className="metric-card metric-plain">
              <dt>시선 이탈</dt>
              <dd>{result.metrics.gaze_off_count ?? "-"}</dd>
            </div>
          </dl>
          <div className="feedback">{result.feedback ?? "피드백 생성 전입니다."}</div>
        </article>
      ))}
    </section>
  );
}
