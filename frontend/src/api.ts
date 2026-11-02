export async function request<T>(url:string, data?:unknown, signal?:AbortSignal):Promise<T> {
  const response = await fetch(url, data === undefined ? {signal} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),signal});
  if (!response.ok) {
    const body = await response.json().catch(()=>({detail:'Błąd połączenia z aplikacją.'}));
    const detail = body.detail;
    throw new Error(Array.isArray(detail) ? detail.map((e:{msg:string;loc:string[]})=>`${e.loc.slice(1).join('.')}: ${e.msg}`).join('\n') : typeof detail==='string' ? detail : 'Nie udało się wykonać operacji.');
  }
  return response.json() as Promise<T>;
}
export function download(data:Blob, filename:string) {
  const url=URL.createObjectURL(data); const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
export async function exportFile(url:string, project:unknown, filename:string) {
  const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(project)});
  if(!res.ok) {const e=await res.json();throw new Error(e.detail || 'Błąd eksportu.');}
  download(await res.blob(),filename);
}
