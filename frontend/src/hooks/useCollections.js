import { useEffect, useMemo, useState } from 'react'
import { getDatasetRecords } from '../api'
const num=v=>Number.isFinite(Number(v))?Number(v):0
const idOf=r=>String(r?.loan_id||r?.id||r?._id||'')
const dateOf=r=>String(r?.snapshot_date||r?.snapshot_month||r?.as_of_date||'').slice(0,10)
const balanceOf=r=>num(r?.outstanding_principal??r?.outstanding_balance??r?.balance)
const dpdOf=r=>num(r?.dpd??r?.days_past_due)
const bucket=d=>d>=90?'90+':d>=60?'60-89':d>=30?'30-59':d>0?'1-29':'current'
function latestTwo(rows){const dates=[...new Set(rows.map(dateOf).filter(Boolean))].sort();if(dates.length<2)return {current:rows,previous:[],currentDate:dates.at(-1)||'',previousDate:''};const currentDate=dates.at(-1),previousDate=dates.at(-2);return {current:rows.filter(r=>dateOf(r)===currentDate),previous:rows.filter(r=>dateOf(r)===previousDate),currentDate,previousDate}}
export function useCollections(datasetId){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(false),[error,setError]=useState('')
 useEffect(()=>{let live=true;if(!datasetId){setRows([]);return}setLoading(true);setError('');getDatasetRecords(datasetId).then(r=>{if(live)setRows(r?.records||[])}).catch(e=>{if(live)setError(e.message||'No se pudo cargar cobranzas')}).finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[datasetId])
 return useMemo(()=>{const {current,previous,currentDate,previousDate}=latestTwo(rows);const prev=new Map(previous.map(r=>[idOf(r),r]));const rollBack=current.filter(r=>prev.has(idOf(r))&&dpdOf(r)<dpdOf(prev.get(idOf(r))));const cures=current.filter(r=>prev.has(idOf(r))&&dpdOf(r)<=0&&dpdOf(prev.get(idOf(r)))>0);const newPar30=current.filter(r=>prev.has(idOf(r))&&dpdOf(r)>=30&&dpdOf(prev.get(idOf(r)))<30).sort((a,b)=>balanceOf(b)-balanceOf(a));const priorities=newPar30.slice(0,20).map(r=>({id:idOf(r),customer_id:r.customer_id||r.client_id||r.customer||idOf(r),balance:balanceOf(r),dpd:dpdOf(r),from_bucket:bucket(dpdOf(prev.get(idOf(r)))),to_bucket:bucket(dpdOf(r)),segment:r.segment||r.product||'—'}));const transitions={};current.forEach(r=>{const p=prev.get(idOf(r));if(!p)return;const k=bucket(dpdOf(p))+' → '+bucket(dpdOf(r));transitions[k]=(transitions[k]||0)+1});return {rows,current,previous,currentDate,previousDate,rollBack,cures,priorities,transitions,available:Boolean(currentDate&&previousDate),loading,error}},[rows,loading,error])
}