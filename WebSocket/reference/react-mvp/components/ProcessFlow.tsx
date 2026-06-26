import { processSteps } from '../lib/mockData';

export function ProcessFlow({ currentStep }: { currentStep: string }) {
  return (
    <section className="panel process-panel">
      <div className="panel-heading">
        <p className="eyebrow">Process</p>
        <h2>공정 흐름</h2>
      </div>
      <div className="process-flow">
        {processSteps.map((step, index) => (
          <div className={`process-step ${step.key === currentStep ? 'active' : ''}`} key={step.key}>
            <div className="step-index">{index + 1}</div>
            <div>
              <div className="step-title">{step.label}</div>
              <div className="step-state">{step.key === currentStep ? 'ACTIVE' : 'WAITING'}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
