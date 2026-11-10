import React from 'react';
import {BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer,Cell,LineChart,Line,CartesianGrid} from 'recharts';
const card='p-5 rounded-2xl bg-white border border-slate-200 shadow-xs min-w-0';
type ChartRow={key:string;name:string;count:number;color?:string};
export function CountChart({id,title,note,rows,trend=false,renderChart=true}:{id:string;title:string;note:string;rows:ChartRow[];trend?:boolean;renderChart?:boolean}){
  return <section data-testid={'analytics-'+id} className={card}>
    <h3 className="font-bold text-sm text-slate-900">{title}</h3><p className="text-xs text-slate-500 mt-1">{note}</p>
    {!rows.length?<p className="py-8 text-sm text-slate-500">No matching records for this chart.</p>:<>
      {renderChart&&<div className="mt-4" style={{height:trend?220:Math.max(180,rows.length*34+35)}} role="img" aria-label={title+' chart'}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          {trend?<LineChart data={rows} margin={{top:12,right:15,left:-12,bottom:8}} accessibilityLayer>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0"/><XAxis dataKey="name" tick={{fontSize:10}} minTickGap={24}/><YAxis allowDecimals={false} tick={{fontSize:11}}/>
            <Tooltip/><Line dataKey="count" name="Incidents" stroke="#2563EB" strokeWidth={2} dot={{r:4}} isAnimationActive={false}/>
          </LineChart>:<BarChart data={rows} layout="vertical" margin={{top:8,right:25,left:0,bottom:4}} accessibilityLayer>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E2E8F0"/><XAxis type="number" allowDecimals={false} tick={{fontSize:11}}/><YAxis type="category" dataKey="name" width={145} tick={{fontSize:11}} interval={0}/>
            <Tooltip cursor={{fill:'#F1F5F9'}}/><Bar dataKey="count" name="Incidents" radius={[0,5,5,0]} isAnimationActive={false}>{rows.map(row=><Cell key={row.key} fill={row.color||'#2563EB'}/>)}</Bar>
          </BarChart>}
        </ResponsiveContainer>
      </div>}
      <details className="mt-2 text-xs"><summary className="text-blue-700 cursor-pointer">View counts</summary><table aria-label={title+' data'} className="w-full mt-2"><thead><tr><th className="text-left font-medium p-1">Category</th><th className="text-right font-medium p-1">Incidents</th></tr></thead><tbody>{rows.map(row=><tr key={row.key} data-key={row.key}><th className="text-left font-normal border-t border-slate-100 p-1 break-words">{row.name}</th><td className="text-right border-t border-slate-100 p-1 tabular-nums">{row.count}</td></tr>)}</tbody></table></details>
    </>}
  </section>;
}
