import React from 'react'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  CircleHelp,
  Download,
  Images,
  RotateCcw,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import { reportUrl, formatDate } from '../lib/api'

export default function ResultsPanel({ result, onBack, onNew }) {
  const audit = result.audit
  const ext = result.extraction
  const category = audit.category || result.category_info || {
    label: result.category || 'Unclassified',
    confidence: ext.category_confidence || 0,
    evidence: ext.category_evidence || [],
  }
  const tone = audit.status === 'compliant' ? 'good' : audit.status === 'non_compliant' ? 'bad' : 'review'
  const statusText = {
    compliant: 'Compliant',
    non_compliant: 'Non-compliant',
    needs_review: 'Needs review',
    manual_review: 'Manual review recommended',
    review: 'Manual review recommended',
  }[audit.status] || 'Review required'
  const penalty = audit.penalty_assessment || { ranges: [] }
  const hasPenaltyRanges = penalty.ranges?.length > 0
  const imageCount = result.image_count || ext.image_count || 1
  const imageFiles = result.image_files || ext.source_images || []

  return <div className="results-view">
    <div className="result-toolbar">
      <button className="text-button" onClick={onBack}><ArrowLeft size={16}/> Back to workspace</button>
      <button className="secondary-button" onClick={() => window.open(reportUrl(result.scan_id), '_blank')}><Download size={16}/> Download inspection report</button>
    </div>

    <section className="result-banner card">
      <div className={`result-icon ${tone}`}>
        {tone === 'good' ? <CheckCircle2 size={25}/> : tone === 'bad' ? <XCircle size={25}/> : <AlertTriangle size={25}/>}
      </div>
      <div className="result-main">
        <div className="eyebrow">AUDIT COMPLETE · {formatDate(result.created_at)}</div>
        <h2>{statusText}</h2>
        <p>{audit.issues_count === 0
          ? 'No missing required declarations were detected in the submitted image.'
          : 'Review the findings below against the full package and applicable product rules.'}</p>
        <div className="category-summary">
          <b>{category.label || category.id}</b>
          <span>{Math.round((category.confidence || 0) * 100)}% category confidence</span>
        </div>
      </div>
      <div className="score-box">
        <span>SCREENING SCORE</span>
        <strong>{audit.score}<small>/100</small></strong>
        <div className="score-track"><i style={{ width: `${audit.score}%` }}/></div>
      </div>
    </section>

    <div className="multi-image-summary">
      <Images size={15}/>
      <span><b>{imageCount} image view{imageCount === 1 ? '' : 's'} combined</b>{imageFiles.length > 0 && <> · {imageFiles.join(', ')}</>}</span>
    </div>
    {category.evidence?.length > 0 && <div className="category-evidence"><b>Classification cues:</b> {category.evidence.join(' · ')}</div>}
    <div className="applicability-strip">
      <span className={`applicability-tag ${audit.fssai_applicable ? 'applies' : 'not-applies'}`}>
        {audit.fssai_applicable ? 'FSSAI food-label checks applied' : 'FSSAI checks not applied'}
      </span>
      <span>{audit.expiry_check === 'required'
        ? 'Product-specific date check applied'
        : audit.expiry_check === 'product_specific'
          ? 'Expiry requirements depend on the specific product rule'
          : 'No generic expiry-date failure for this category'}</span>
    </div>

    <div className="result-grid">
      <section className="card checks-card">
        <div className="card-heading">
          <div>
            <h3>Applicable declaration checks</h3>
            <p>{audit.checks.length} checks · Automatically selected for {category.label || category.id}</p>
          </div>
          <span className="finding-badge">{audit.issues_count} finding{audit.issues_count === 1 ? '' : 's'}</span>
        </div>
        <div className="check-list">
          {audit.checks.map(check => <div className="check-row" key={check.id}>
            <div className={`check-status ${check.status}`}>
              {check.status === 'pass' ? <CheckCircle2 size={17}/> : check.status === 'fail' ? <XCircle size={17}/> : <CircleHelp size={17}/>}
            </div>
            <div className="check-copy">
              <b>{check.label}</b>
              <span>{check.reference} · {check.detail}</span>
              {check.value && <em>Detected: {check.value}</em>}
            </div>
            <span className={`check-tag ${check.status}`}>
              {check.status === 'pass' ? 'Detected' : check.status === 'fail' ? 'Missing' : check.status === 'not_applicable' ? 'Not applicable' : 'Review'}
            </span>
          </div>)}
        </div>
      </section>

      <aside className="result-aside">
        <section className="card detail-card">
          <div className="card-heading">
            <div><h3>Extracted label details</h3><p>Text read from the submitted image set</p></div>
            <span className="confidence">{Math.round((ext.confidence || 0) * 100)}% text confidence</span>
          </div>
          <dl>
            <dt>Product</dt><dd>{ext.product_name || 'Not detected'}</dd>
            <dt>Net quantity</dt><dd>{ext.net_quantity || 'Not detected'}</dd>
            <dt>MRP</dt><dd>{ext.mrp || 'Not detected'}</dd>
            <dt>Pack date</dt><dd>{ext.pack_date || 'Not detected'}</dd>
            {audit.fssai_applicable && <><dt>FSSAI licence</dt><dd>{ext.fssai_license_number || 'Not detected'}</dd></>}
            {audit.expiry_check !== 'not_generally_required' && <><dt>Expiry / use by</dt><dd>{ext.expiry_date || 'Not detected'}</dd></>}
            <dt>Consumer care</dt><dd>{ext.consumer_care || 'Not detected'}</dd>
            <dt>Batch / lot</dt><dd>{ext.batch_number || 'Not detected'}</dd>
          </dl>
        </section>

        {hasPenaltyRanges && <section className="card fine-card">
          <div className="eyebrow">CONDITIONAL PENALTY SCHEDULE</div>
          <h3>{penalty.headline}</h3>
          {penalty.ranges.map((range, index) => <div className="penalty-range" key={`${range.law}-${index}`}>
            <b>{range.stage}</b>
            <strong>{range.minimum_inr === 0 && range.maximum_inr === 0
              ? 'Improvement notice'
              : range.minimum_inr === range.maximum_inr
                ? `₹${Number(range.maximum_inr).toLocaleString('en-IN')}`
                : range.minimum_inr === 0
                  ? `Up to ₹${Number(range.maximum_inr).toLocaleString('en-IN')}`
                  : `₹${Number(range.minimum_inr).toLocaleString('en-IN')}–₹${Number(range.maximum_inr).toLocaleString('en-IN')}`}</strong>
            <span>{range.law}</span>
            <small>{range.qualifier}</small>
          </div>)}
          <p>{penalty.basis}</p>
          <div className="fine-disclaimer"><CircleHelp size={15}/> Statutory ranges only, not a calculated payable fine. Verify the offence stage and authority in official records. Keep separate legal routes separate.</div>
        </section>}
      </aside>
    </div>

    <div className="result-bottom">
      <span><ShieldCheck size={15}/> AI-assisted screening · Confirm classification and rules before enforcement decisions.</span>
      <button className="primary-button" onClick={onNew}><RotateCcw size={15}/> Start another audit</button>
    </div>
  </div>
}
