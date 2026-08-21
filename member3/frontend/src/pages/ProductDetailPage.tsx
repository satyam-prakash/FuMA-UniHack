/**
 * Single-record inspector. Three columns when the row matches a labelled
 * ground-truth record, two otherwise.
 *
 * Each generated description carries its own character count and a pass/fail
 * chip against its own limit, so the invoice-40 rule and the mobile window are
 * judged separately rather than rolled into one "quality" number.
 */

import { useEffect, useState } from 'react';
import { ArrowLeft, ChevronDown, ChevronRight } from '../components/icons';
import { getRow } from '../api/client';
import { PageHeader } from '../components/AppShell';
import Button from '../components/Button';
import DiffPanel, { type DiffField } from '../components/DiffPanel';
import Plate from '../components/Plate';
import StatChip, { PassChip, StatusChip } from '../components/StatChip';
import { DESCRIPTION_LIMITS, enrichedOf, type DescriptionKey, type RowDetail } from '../types';

const DESCRIPTIONS: { key: DescriptionKey; label: string }[] = [
  { key: 'invoice_desc', label: 'INVOICE_DESC' },
  { key: 'mobile_desc', label: 'MOBILE_DESC' },
  { key: 'short_desc', label: 'SHORT_DESC' },
  { key: 'long_desc1', label: 'LONG_DESC1' },
  { key: 'retail_desc', label: 'RETAIL_DESC' },
];

/** Loose equality so casing and spacing noise does not read as a real change. */
function same(a: string, b: string): boolean {
  const flatten = (value: string) => value.trim().toLowerCase().replace(/\s+/g, ' ');
  return flatten(a) === flatten(b);
}

export default function ProductDetailPage({
  jobId,
  rowId,
  onBack,
}: {
  jobId: string;
  rowId: number;
  onBack: () => void;
}) {
  const [row, setRow] = useState<RowDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showDelivery, setShowDelivery] = useState(false);

  useEffect(() => {
    let live = true;
    getRow(jobId, rowId)
      .then((data) => live && setRow(data))
      .catch((cause) => live && setError(String(cause)));
    return () => {
      live = false;
    };
  }, [jobId, rowId]);

  if (error) {
    return (
      <div className="border border-error bg-error-container px-4 py-3 font-data-mono text-data-mono text-on-error-container">
        {error}
      </div>
    );
  }

  if (!row) {
    return <div className="h-64 border border-border-subtle bg-surface-container-low" />;
  }

  const enriched = enrichedOf(row);
  const truth = row.ground_truth;
  // Static classes only: Tailwind's JIT cannot see an interpolated col-span.
  const columnClass = truth ? 'col-span-12 lg:col-span-4' : 'col-span-12 lg:col-span-6';

  const rawFields: DiffField[] = [
    { label: 'Mfg_Part_Num', value: row.raw.Mfg_Part_Num ?? '' },
    { label: 'Part_Desc', value: row.raw.Part_Desc ?? '' },
    { label: 'E1_Brand', value: row.raw.E1_Brand ?? '' },
    { label: 'Unilog_Brand', value: row.raw.Unilog_Brand ?? '' },
    { label: 'DIB_Brand', value: row.raw.DIB_Brand ?? '' },
    { label: 'Part_Manuf', value: row.raw.Part_Manuf ?? '' },
  ];

  const generatedFields: DiffField[] = [
    {
      label: 'MANUFACTURER_PART_NUMBER',
      value: enriched.mfg_part_num,
      changed: !same(enriched.mfg_part_num, row.raw.Mfg_Part_Num ?? ''),
    },
    {
      label: 'MANUFACTURER_NAME',
      value: enriched.manufacturer_name,
      changed: !same(enriched.manufacturer_name, row.raw.Part_Manuf ?? ''),
    },
    {
      label: 'BRAND_NAME',
      value: enriched.brand_name,
      changed: !same(enriched.brand_name, row.raw.E1_Brand ?? ''),
    },
    { label: 'SERIES', value: enriched.series, changed: Boolean(enriched.series) },
    { label: 'Product Name', value: enriched.product_name, changed: Boolean(enriched.product_name) },
    { label: 'Classpath', value: enriched.classpath, changed: Boolean(enriched.classpath) },
    { label: 'UNSPSC', value: enriched.unspsc, changed: Boolean(enriched.unspsc) },
    {
      label: 'Confidence',
      value: row.confidence.toFixed(1),
      note: `${enriched.attributes.length} attributes \u00b7 ${enriched.features.length} features`,
    },
  ];

  const truthFields: DiffField[] = truth
    ? [
        { label: 'MANUFACTURER_PART_NUMBER', value: truth.MANUFACTURER_PART_NUMBER ?? '' },
        {
          label: 'MANUFACTURER_NAME',
          value: truth.MANUFACTURER_NAME ?? '',
          changed: !same(truth.MANUFACTURER_NAME ?? '', enriched.manufacturer_name),
        },
        {
          label: 'BRAND_NAME',
          value: truth.BRAND_NAME ?? '',
          changed: !same(truth.BRAND_NAME ?? '', enriched.brand_name),
        },
        { label: 'SERIES', value: truth.SERIES ?? '' },
        {
          label: 'Product Name',
          value: truth['Product Name'] ?? '',
          changed: !same(truth['Product Name'] ?? '', enriched.product_name),
        },
        {
          label: 'Classpath',
          value: truth.Classpath ?? '',
          changed: !same(truth.Classpath ?? '', enriched.classpath),
        },
        {
          label: 'UNSPSC',
          value: truth.UNSPSC ?? '',
          changed: !same(truth.UNSPSC ?? '', enriched.unspsc),
        },
      ]
    : [];

  return (
    <>
      <PageHeader
        title="Product Inspector"
        meta={[
          { label: 'row', value: String(row.row_id) },
          { label: 'mpn', value: enriched.mfg_part_num || row.mpn || '\u2014' },
          { label: 'status', value: row.status.toUpperCase() },
        ]}
        actions={
          <Button variant="secondary" onClick={onBack}>
            <ArrowLeft size={14} strokeWidth={2} /> Back to dashboard
          </Button>
        }
      />

      {/* Comparison columns */}
      <section className="grid grid-cols-12 gap-gutter mb-gutter">
        <div className={columnClass}>
          <DiffPanel idx={1} heading="Raw input" subheading="Supplier row" fields={rawFields} />
        </div>
        <div className={columnClass}>
          <DiffPanel
            idx={2}
            heading="Generated"
            subheading={'M1 \u2192 M2 output'}
            fields={generatedFields}
            emphasis
          />
        </div>
        {truth && (
          <div className={columnClass}>
            <DiffPanel
              idx={3}
              heading="Ground truth"
              subheading="Labelled delivery row"
              fields={truthFields}
            />
          </div>
        )}
      </section>

      {/* Descriptions */}
      <section className="mb-gutter">
        <Plate idx={4} label="Generated descriptions">
          <div className="flex flex-col gap-5">
            {DESCRIPTIONS.map(({ key, label }) => {
              const text = enriched[key];
              const limit = DESCRIPTION_LIMITS[key];
              // Invoice must also be uppercase; mobile is judged twice on purpose.
              const withinLimit = text.length > 0 && text.length <= limit;
              return (
                <div key={key} className="border-b border-border-subtle pb-4 last:border-b-0">
                  <div className="flex flex-wrap items-center gap-3 mb-2">
                    <span className="font-label-caps text-label-caps text-secondary uppercase">
                      {label}
                    </span>
                    <span className="font-data-mono text-annotation text-ink-graphite">
                      {text.length}/{limit}
                    </span>
                    <PassChip pass={withinLimit} />
                    {key === 'invoice_desc' && (
                      <PassChip
                        pass={row.validation.invoice_caps}
                        label={row.validation.invoice_caps ? 'CAPS OK' : 'CAPS FAIL'}
                      />
                    )}
                    {key === 'mobile_desc' && (
                      <>
                        <PassChip
                          pass={row.validation.schema_mobile_pass}
                          label={`SCHEMA \u2264 85 ${row.validation.schema_mobile_pass ? 'PASS' : 'FAIL'}`}
                        />
                        <PassChip
                          pass={row.validation.mobile_target_pass}
                          label={`TARGET 60-80 ${row.validation.mobile_target_pass ? 'PASS' : 'FAIL'}`}
                        />
                      </>
                    )}
                  </div>
                  <p className="font-body-md text-body-md text-ink-graphite break-words">
                    {text || '\u2014'}
                  </p>
                </div>
              );
            })}
          </div>
        </Plate>
      </section>

      {/* Attributes + review */}
      <section className="grid grid-cols-12 gap-gutter mb-gutter">
        <div className="col-span-12 lg:col-span-7">
          <Plate idx={5} label={`Technical attributes (${enriched.attributes.length})`}>
            {enriched.attributes.length === 0 ? (
              <div className="font-data-mono text-data-mono text-secondary uppercase">
                No attributes extracted
              </div>
            ) : (
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b border-ink-graphite">
                    {['Label', 'Value', 'UOM'].map((heading) => (
                      <th
                        key={heading}
                        className="text-left font-label-caps text-label-caps text-secondary uppercase pb-2"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {enriched.attributes.map((attribute, index) => (
                    <tr
                      key={`${attribute.label}-${index}`}
                      className="border-b border-border-subtle last:border-b-0"
                    >
                      <td className="py-2 pr-4 font-data-mono text-data-mono text-secondary">
                        {attribute.label}
                      </td>
                      <td className="py-2 pr-4 font-data-mono text-data-mono text-ink-graphite">
                        {attribute.value}
                      </td>
                      <td className="py-2 font-data-mono text-annotation text-secondary uppercase">
                        {attribute.uom || '\u2014'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Plate>
        </div>

        <div className="col-span-12 lg:col-span-5">
          <Plate idx={6} label="Validation & review">
            <div className="flex flex-wrap gap-2 mb-5">
              <StatusChip status={row.status} />
              <PassChip
                pass={row.validation.schema_valid}
                label={`SCHEMA ${row.validation.schema_valid ? 'VALID' : 'INVALID'}`}
              />
              <StatChip tone="neutral">{row.validation.attribute_count} ATTRS</StatChip>
              {row.review.categories.map((category) => (
                <StatChip key={category} tone="warn">
                  {category.replace(/_/g, ' ')}
                </StatChip>
              ))}
              {row.review.decision && (
                <StatChip tone="accent">{row.review.decision.replace('_', ' ')}</StatChip>
              )}
            </div>

            {row.review.reasons.length === 0 ? (
              <div className="font-data-mono text-data-mono text-secondary uppercase">
                No review reasons
              </div>
            ) : (
              <ul className="flex flex-col">
                {row.review.reasons.map((reason) => (
                  <li
                    key={reason}
                    className="py-2 border-b border-border-subtle last:border-b-0 font-body-md text-body-md text-ink-graphite border-l-2 border-l-primary pl-3"
                  >
                    {reason}
                  </li>
                ))}
              </ul>
            )}

            {row.validation.schema_errors.length > 0 && (
              <div className="mt-5 border border-error bg-error-container p-3">
                <div className="font-label-caps text-label-caps text-on-error-container uppercase mb-1">
                  Schema errors
                </div>
                {row.validation.schema_errors.map((message) => (
                  <div
                    key={message}
                    className="font-data-mono text-annotation text-on-error-container"
                  >
                    {message}
                  </div>
                ))}
              </div>
            )}
            {row.error && (
              <div className="mt-5 border border-error bg-error-container p-3">
                <div className="font-label-caps text-label-caps text-on-error-container uppercase mb-1">
                  Stage failure: {row.error.stage}
                </div>
                <div className="font-data-mono text-annotation text-on-error-container">
                  [{row.error.code}] {row.error.message}
                </div>
              </div>
            )}
          </Plate>
        </div>
      </section>

      {/* Full delivery field drawer */}
      <section>
        <button
          type="button"
          onClick={() => setShowDelivery((open) => !open)}
          className="w-full flex items-center gap-3 border border-ink-graphite bg-surface-bright px-4 py-3 font-label-caps text-label-caps text-ink-graphite uppercase hover:bg-surface-variant transition-colors"
        >
          {showDelivery ? (
            <ChevronDown size={16} strokeWidth={2} />
          ) : (
            <ChevronRight size={16} strokeWidth={2} />
          )}
          Full delivery field set
          <span className="ml-auto font-data-mono text-annotation text-secondary">
            RAW {Object.keys(row.raw).length} + M1 {Object.keys(row.normalized).length} FIELDS
          </span>
        </button>

        {showDelivery && (
          <div className="border border-t-0 border-ink-graphite bg-surface-bright p-6 grid grid-cols-1 md:grid-cols-2 gap-x-gutter">
            {[
              ...Object.entries(row.raw).map(([key, value]) => ({ key, value: String(value), m1: false })),
              ...Object.entries(row.normalized).map(([key, value]) => ({
                key,
                value: value === null ? '' : String(value),
                m1: true,
              })),
            ]
              // M1 echoes the raw row back, so drop the duplicate keys.
              .filter((entry, index, all) => all.findIndex((other) => other.key === entry.key) === index)
              .map((entry) => (
                <div
                  key={entry.key}
                  className={[
                    'flex justify-between gap-4 py-2 border-b border-border-subtle',
                    entry.m1 ? 'border-l-2 border-l-primary pl-3' : '',
                  ].join(' ')}
                >
                  <span className="font-label-caps text-annotation text-secondary uppercase shrink-0">
                    {entry.key}
                  </span>
                  <span className="font-data-mono text-annotation text-ink-graphite text-right break-words">
                    {entry.value || '\u2014'}
                  </span>
                </div>
              ))}
          </div>
        )}
      </section>
    </>
  );
}
