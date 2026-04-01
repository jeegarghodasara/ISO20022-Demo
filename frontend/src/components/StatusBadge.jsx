const statusConfig = {
  ACTC: { label: 'Technical OK', className: 'badge-blue' },
  ACCP: { label: 'Accepted', className: 'badge-purple' },
  ACSP: { label: 'Processing', className: 'badge-orange' },
  ACSC: { label: 'Settled', className: 'badge-success' },
  RJCT: { label: 'Rejected', className: 'badge-red' },
  PDNG: { label: 'Pending', className: 'badge-orange' },
  CANC: { label: 'Cancelled', className: 'badge-red' },
  OPEN: { label: 'Open', className: 'badge-orange' },
  PENDING: { label: 'Pending', className: 'badge-orange' },
  RESOLVED: { label: 'Resolved', className: 'badge-success' },
  CLOSED: { label: 'Closed', className: 'badge-blue' },
  ACTV: { label: 'Active', className: 'badge-success' },
  SUSP: { label: 'Suspended', className: 'badge-orange' },
}

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || { label: status, className: 'badge-blue' }
  return <span className={`badge ${config.className}`}>{config.label}</span>
}
