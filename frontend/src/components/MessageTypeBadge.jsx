const typeConfig = {
  'pacs.008': { label: 'Credit Transfer', className: 'badge-success' },
  'pacs.009': { label: 'Bank Transfer', className: 'badge-blue' },
  'pacs.004': { label: 'Payment Return', className: 'badge-orange' },
  'pain.001': { label: 'Initiation', className: 'badge-purple' },
  'pain.008': { label: 'Direct Debit', className: 'badge-teal' },
}

export const MESSAGE_TYPE_LABELS = {
  'pacs.008': 'Customer Credit Transfer',
  'pacs.009': 'Bank-to-Bank Transfer',
  'pacs.004': 'Payment Return',
  'pain.001': 'Payment Initiation',
  'pain.008': 'Direct Debit Initiation',
}

export default function MessageTypeBadge({ type }) {
  const config = typeConfig[type] || { label: type, className: 'badge-blue' }
  return <span className={`badge ${config.className}`}>{config.label}</span>
}
