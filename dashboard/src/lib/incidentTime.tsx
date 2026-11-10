import React from 'react';

export function IncidentTime({value}:{value?:string|null}) {
  if (!value) return <span>Not recorded</span>;
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return <span>{value}</span>;
  return <time dateTime={date.toISOString()} title={date.toISOString()}>{new Intl.DateTimeFormat(undefined, {
    year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short',
  }).format(date)}</time>;
}
